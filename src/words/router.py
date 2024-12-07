import redis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitions.dependencies import get_cache_service
from src.constants import AvailableLanguages
from src.database import get_async_session, get_redis
from src.quizzes.constants import AvailablePartOfSpeech, AvailableWordLevel
from src.quizzes.schemas import UserFavoriteWord
from src.words.query import get_available_languages, get_available_part_of_speech
from src.words.schemas import WordSchema, SentenceSchema
from src.words.service import (FavoriteWordManager,
                               SentenceManager,
                               WordManager, CacheRedisService)

router = APIRouter(
    prefix="/words",
    tags=["words"]
)


@router.post("/add-word")
async def add_word(word_data: WordSchema, session: AsyncSession = Depends(get_async_session)
):
    word_service = WordManager(session)
    return await word_service.add_word(word_data)


@router.post("/add-sentence")
async def add_sentence(sentence_data: SentenceSchema, session: AsyncSession = Depends(get_async_session)
):
    sentence_service = SentenceManager(session)
    return await sentence_service.add_sentence(sentence_data)


@router.post("/favorite-word")
async def add_favorite_word(data: UserFavoriteWord, session: AsyncSession = Depends(get_async_session)):
    favorite_word_service = FavoriteWordManager(session)
    return await favorite_word_service.add_favorite_word(data)


@router.delete("/favorite-word")
async def delete_favorite_word(data: UserFavoriteWord, session: AsyncSession = Depends(get_async_session)):
    favorite_word_service = FavoriteWordManager(session)
    return await favorite_word_service.delete_favorite_word(data)


@router.get("/check-available-language")
async def check_available_language(
        session: AsyncSession = Depends(get_async_session),
        cache_service: CacheRedisService = Depends(get_cache_service)
):
    word_manager = WordManager(session)
    available_languages = await word_manager.get_languages(cache_service)
    return available_languages


@router.get("/check-available-part-of-speech")
async def check_available_part_of_speech(
        session: AsyncSession = Depends(get_async_session),
        cache_service: CacheRedisService = Depends(get_cache_service)
):
    word_manager = WordManager(session)
    return await word_manager.get_parts_of_speech(cache_service)
