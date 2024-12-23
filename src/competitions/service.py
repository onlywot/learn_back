import asyncio
import json
from typing import Sequence

import redis.asyncio as redis
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from fastapi import HTTPException
from fastapi.websockets import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..quizzes.query import get_translation_words
from ..quizzes.schemas import RandomWordResponse
from ..quizzes.service import QuizResponseService, WordService
from ..users.query import get_user_by_telegram_id
from ..utils import commit_changes_or_rollback
from .models import CompetitionRoom, CompetitionRoomData
from .query import (get_all_users_stats, get_competition, get_room_data,
                    get_rooms, get_user_room_data, get_user_rooms_data,
                    get_users_count_in_room)
from .schemas import CompetitionAnswerSchema, CompetitionRoomSchema, CompetitionsAnswersSchema, CompetitionSchema


class WebSocketManager:
    def __init__(self):
        self.websockets = {}

    async def add_connection(self, telegram_id: int, websocket: WebSocket) -> None:
        self.websockets[telegram_id] = websocket

    async def remove_connections(self, telegram_id: int, session: AsyncSession, room_manager: "RoomManager") -> None:
        self.websockets.pop(telegram_id, None)
        await RoomService.change_user_status(telegram_id, "offline", session)
        await room_manager.remove_user_from_room(telegram_id, self, session)

    async def room_broadcast_message(self, room_id: int, message: str, room_manager: "RoomManager") -> None:
        telegram_ids = await room_manager.get_users_in_room(room_id)
        for telegram_id in telegram_ids:
            websocket = self.websockets.get(int(telegram_id))
            if websocket:
                await websocket.send_text(message)

    async def notify_all_users(self, message: str) -> None:
        for websocket in self.websockets.values():
            await websocket.send_text(message)

    async def notify_user(self, telegram_id: int, room_id: int):
        if telegram_id in self.websockets:
            message = await MessageService.create_invite_to_room_message(room_id)
            await self.websockets[telegram_id].send_text(json.dumps(message))


class RoomManager:

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    @staticmethod
    async def get_rooms_list(session: AsyncSession) -> list:
        async with session:
            rooms = await get_rooms(session)
            rooms_list = []
            for room, online_count in rooms:
                room = room.__dict__
                room.update({"online_count": online_count})
                rooms_list.append(room)
            return rooms_list

    async def create_room(
            self, room_data: CompetitionSchema, websocket_manager: WebSocketManager, session: AsyncSession
    ) -> None:
        async with session as session:
            user = await get_user_by_telegram_id(session, room_data.telegram_id)
            new_room = CompetitionRoom(owner_id=user.id, **room_data.dict(exclude={"telegram_id"}))
            session.add(new_room)
            await commit_changes_or_rollback(session, "Ошибка при создании комнаты")
            await websocket_manager.notify_all_users(MessageService.create_new_room_message(new_room, user))

    async def add_user_to_room(self, telegram_id: int, room_id: int) -> None:
        await self.redis.sadd(f"room:{room_id}", telegram_id)
        await self.redis.hset("user_room_map", str(telegram_id), str(room_id))

    async def remove_user_from_room(
            self, telegram_id: int, websocket_manager: WebSocketManager, session: AsyncSession, room_id: int = None
    ) -> None:
        if room_id is None:
            room_id = await self.redis.hget("user_room_map", str(telegram_id))
            if not room_id:
                return
            user = await get_user_by_telegram_id(session, telegram_id)
            room_data = await get_room_data(int(room_id), session)
            await websocket_manager.notify_all_users(
                json.dumps(await MessageService.create_user_move_message("leave", user, room_data, session))
            )
        await self.redis.srem(f"room:{int(room_id)}", telegram_id)
        await self.redis.hdel("user_room_map", str(telegram_id))

    async def get_users_in_room(self, room_id: int) -> list[int]:
        users = await self.redis.smembers(f"room:{room_id}")
        return [int(user) for user in users]


class RoomService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_user_room_data(
            self, room_data: CompetitionRoomSchema, action: str, websocket_manager: WebSocketManager,
            room_manager: RoomManager, redis_client: redis.Redis
    ):
        async with self.session as session:
            telegram_id, room_id = room_data.telegram_id, room_data.room_id
            user = await get_user_by_telegram_id(session, telegram_id)
            room_data = await get_room_data(room_id, session)
            user_room_data = await get_user_room_data(room_id, user.id, session)

            if action == "join":
                return await self.user_join(
                    room_id, telegram_id, user.id, user_room_data, room_manager, session, websocket_manager,
                    redis_client
                )

            elif action == "leave":
                await self.user_leave(
                    room_id, telegram_id, user_room_data, room_manager, websocket_manager, user, room_data, session
                )

    async def user_join(self, room_id: int, telegram_id: int, user_id: int, user_room_data: CompetitionRoomData,
                        room_manager: RoomManager, session: AsyncSession, websocket_manager: WebSocketManager,
                        redis_client: redis
                        ):
        room_data = await get_room_data(room_id, self.session)
        user = await get_user_by_telegram_id(self.session, telegram_id)
        await self.__change_user_status_to_online(room_id, user_id, user_room_data)
        await room_manager.add_user_to_room(telegram_id, room_id)
        message_for_users = await MessageService.create_user_move_message("join", user, room_data, session)
        await websocket_manager.notify_all_users(json.dumps(message_for_users))
        current_question = await CompetitionService.get_current_question(room_id, redis_client)
        message_for_users["current_question"] = current_question
        return message_for_users

    async def user_leave(
            self, room_id: int, telegram_id: int, user_room_data: CompetitionRoomData, room_manager: RoomManager,
            websocket_manager: WebSocketManager, user: User, room_data: CompetitionRoom, session: AsyncSession
    ):
        await self.__change_user_status_to_offline(user_room_data)
        await room_manager.remove_user_from_room(telegram_id, websocket_manager, self.session, room_id)
        message_for_users = await MessageService.create_user_move_message("leave", user, room_data, session)
        await websocket_manager.notify_all_users(json.dumps(message_for_users))

    async def __change_user_status_to_offline(self, user_room_data: CompetitionRoomData) -> None:
        async with self.session as session:
            user_room_data.user_status = "offline"
            await commit_changes_or_rollback(session, "Ошибка при обновлении данных")

    async def __change_user_status_to_online(self, room_id: int, user_id: int,
                                             user_room_data: CompetitionRoomData) -> None:
        async with self.session as session:
            if not user_room_data:
                await self.__create_user_room_data(room_id, user_id)
            else:
                user_room_data.user_status = "online"
                await commit_changes_or_rollback(session, "Ошибка при подключении в комнату")

    async def __create_user_room_data(self, room_id: int, user_id: int) -> None:
        async with self.session as session:
            new_user_room_data = CompetitionRoomData(competition_id=room_id, user_id=user_id, user_status="online")
            session.add(new_user_room_data)
            await commit_changes_or_rollback(session, "Ошибка при подключении в комнату")

    @staticmethod
    async def send_invite(telegram_id: int, room_id: int, bot: Bot, websocket_manager: WebSocketManager):
        if telegram_id in websocket_manager.websockets:
            await websocket_manager.notify_user(telegram_id, room_id)
            return {"type": "send_invite", "success": True}
        button = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
            [InlineKeyboardButton(
                text='Присоединиться',
                web_app=WebAppInfo(url=f"https://learn-mirash.netlify.app/rooms/{room_id}")
            )]])
        await bot.send_message(chat_id=telegram_id, text="Приглашение в комнату", reply_markup=button)
        return {"type": "send_telegram_invite", "success": True}

    @staticmethod
    async def change_user_status(telegram_id: int, status: str, session: AsyncSession) -> None:
        async with session:
            user = await get_user_by_telegram_id(session, telegram_id)
            user_rooms_data = await get_user_rooms_data(user.id, session)
            for room in user_rooms_data:
                room.user_status = status
            await commit_changes_or_rollback(session, "Ошибка при обновлении данных")

    @staticmethod
    async def change_status_room_to_active(room_id: int, session: AsyncSession):
        competition_room = await get_competition(room_id, session)
        if competition_room.status == "active":
            return False
        competition_room.status = "active"
        await commit_changes_or_rollback(session, "Ошибка при обновлении данных")
        return True


class CompetitionService:
    button_block = False

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(
            self, room_id: int, websocket_manager: WebSocketManager, room_manager: RoomManager,
            redis_client: redis.Redis):
        async with self.session as session:
            change_status = await RoomService.change_status_room_to_active(room_id, session)
            if not change_status:
                error_response = MessageService.create_error_message("Can't start, the game is already in progress")
                return error_response
            room_data = await get_competition(room_id, session)
            response = await CompetitionService.prepare_competition_words(room_data, session, redis_client)
            await websocket_manager.room_broadcast_message(room_id, response.json(), room_manager)

    @staticmethod
    async def prepare_competition_words(
            room_data: CompetitionRoom, session: AsyncSession, redis_client: redis.Redis
                                        ) -> RandomWordResponse:
        async with session:
            word_service = WordService(session)
            random_words = await word_service.get_random_words(room_data.language_from_id, room_data.language_to_id)

            response = QuizResponseService.create_random_word_response(
                random_words["word_for_translate"], random_words["other_words"]
            )
            await CompetitionService.save_current_question(room_data.id, response, redis_client)
            return response

    async def check_competition_answer(
            self, answer_data: CompetitionAnswerSchema, websocket_manager: WebSocketManager, room_manager: RoomManager,
            redis_client: redis.Redis
    ):
        if CompetitionService.button_block:
            return
        room_data = await get_room_data(answer_data.room_id, self.session)
        if room_data.status != "active":
            error_response = MessageService.create_error_message("The game hasn't started yet")
            return error_response
        CompetitionService.button_block = True
        try:
            result = await self.__check_answer(answer_data)
            await self.__update_user_statistics(answer_data, result)
            await self.send_competition_answer(result, answer_data, room_manager, websocket_manager, redis_client)
        finally:
            CompetitionService.button_block = False

    async def send_competition_answer(
            self, result: bool, answer_data: CompetitionAnswerSchema,
            room_manager: RoomManager, websocket_manager: WebSocketManager, redis_client: redis.Redis
    ):
        users_stats = await self.get_users_stats(answer_data.room_id)

        await self.send_answer_response(answer_data, result, users_stats, websocket_manager, room_manager)
        await self.send_new_question(answer_data, websocket_manager, room_manager, redis_client)

    async def send_answer_response(
            self, answer_data: CompetitionAnswerSchema, result: bool,
            users_stats: Sequence[CompetitionRoomData], websocket_manager: WebSocketManager, room_manager: RoomManager
    ):
        response = await ResponseCompetitionsService.create_competition_answer_response(
            answer_data, result, users_stats, self.session)
        await websocket_manager.room_broadcast_message(answer_data.room_id, response.json(), room_manager)

    async def send_new_question(
            self, answer_data: CompetitionAnswerSchema, websocket_manager: WebSocketManager, room_manager: RoomManager,
            redis_client: redis.Redis
    ):
        await asyncio.sleep(3)
        await self.remove_current_answer(answer_data.room_id, redis_client)
        new_question = await ResponseCompetitionsService.create_new_questions_response(
            answer_data, self.session, redis_client
        )
        await websocket_manager.room_broadcast_message(answer_data.room_id, new_question.json(), room_manager)

    async def __check_answer(self, answer_data: CompetitionAnswerSchema) -> bool:
        async with self.session as session:
            translation_word = await get_translation_words(session, answer_data.word_for_translate_id)
            return answer_data.user_word_id == translation_word.id

    async def __update_user_statistics(self, answer_data: CompetitionAnswerSchema, result: bool) -> None:
        async with self.session as session:
            user = await get_user_by_telegram_id(session, answer_data.telegram_id)
            await self.__update_competition_statistics(user, answer_data.room_id, result)

    async def get_users_stats(self, room_id: int) -> Sequence[CompetitionRoomData]:
        async with self.session as session:
            return await get_all_users_stats(room_id, session)

    async def __update_competition_statistics(self, user: User, room_id: int, result: bool) -> None:
        async with self.session as session:
            user_room_data = await get_user_room_data(room_id, user.id, session)
            user_room_data.user_points += 10 if result else -10
            await commit_changes_or_rollback(session, "Ошибка при обновлении данных")

    @staticmethod
    async def save_current_question(room_id, current_question: RandomWordResponse, redis_client: redis.Redis):
        await redis_client.hset("room_question", room_id, current_question.json())

    @staticmethod
    async def remove_current_answer(room_id, redis_client: redis.Redis):
        await redis_client.hdel("room_question", room_id)

    @staticmethod
    async def get_current_question(room_id, redis_client: redis.Redis):
        current_question = await redis_client.hget("room_question", room_id)
        if not current_question:
            return None
        return json.loads(current_question)


class MessageService:

    @staticmethod
    def create_error_message(message: str) -> HTTPException:
        raise HTTPException(status_code=403, detail=message)

    @staticmethod
    async def create_invite_to_room_message(room_id: int):
        return {"type": "invite", "room_id": room_id}

    @staticmethod
    async def create_user_move_message(
            action: str, user: User, room_data: CompetitionRoom, session: AsyncSession
    ) -> dict:
        users_count = await get_users_count_in_room(room_data.id, session)
        users_stats = await get_all_users_stats(room_data.id, session)
        return {
            "type": f"user_{action}",
            "room_id": room_data.id,
            "username": user.username,
            "status_room": room_data.status,
            "users_count": users_count,
            "users": [{
                "username": user.user.username,
                "user_photo_url": user.user.photo_url,
                "points": user.user_points} for user in users_stats]
        }

    @staticmethod
    def create_new_room_message(room: CompetitionRoom, user: User) -> str:
        return json.dumps({
            "type": "created_new_room",
            "room_data": {
                "room_id": room.id, "owner": user.username,
                "language_from_id": room.language_from_id,
                "language_to_id": room.language_to_id
            }
        })

    @staticmethod
    def create_competition_answer_message(
            user: User, result: bool, answer_data: CompetitionAnswerSchema, translation_word_id: int,
            users_stats: Sequence[CompetitionRoomData]
    ):
        response_data = {
            "type": "check_competition_answer",
            "answered_user": {
                "username": user.username, "user_photo_url": user.photo_url, "success": result},
            "selected_word_id": answer_data.user_word_id,
            "correct_word_id": translation_word_id,
            "users": [{
                "username": user.user.username,
                "user_photo_url": user.user.photo_url,
                "points": user.user_points} for user in users_stats]
        }
        return response_data


class ResponseCompetitionsService:

    @staticmethod
    async def create_competition_answer_response(
            answer_data: CompetitionAnswerSchema, result: bool,
            users_stats: Sequence[CompetitionRoomData], session: AsyncSession):
        async with session:
            user = await get_user_by_telegram_id(session, answer_data.telegram_id)
            translation_word = await get_translation_words(session, answer_data.word_for_translate_id)

            response_data = MessageService.create_competition_answer_message(
                user, result, answer_data, translation_word.id, users_stats
            )
            response = CompetitionsAnswersSchema(**response_data)
            return response

    @staticmethod
    async def create_new_questions_response(
            answer_data: CompetitionAnswerSchema, session: AsyncSession, redis_client: redis.Redis
    ):
        room_data = await get_room_data(answer_data.room_id, session)
        new_question = await CompetitionService.prepare_competition_words(room_data, session, redis_client)
        return new_question
