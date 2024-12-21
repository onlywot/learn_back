import uuid
from typing import List

from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.quizzes.query import (get_random_sentence_for_translate,
                               get_random_user_favorite_word,
                               get_random_word_for_translate, get_random_words,
                               get_random_words_for_match,
                               get_random_words_for_sentence,
                               get_sentence_translation, get_translation_words,
                               get_user_favorite_words)
from src.quizzes.schemas import (MatchWordsResponse, RandomSentenceResponse,
                                 RandomWordResponse)
from src.quizzes.utils import (add_word_for_translate_to_other_words,
                               delete_punctuation, shuffle_random_words)
from src.words.schemas import SentenceInfo, WordInfo
from src.users.query import get_user_by_telegram_id


class WordService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_random_word(
            self,
            telegram_id: int) -> RandomWordResponse:
        async with self.session as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            words = await self.get_random_words(user.learning_language_from_id, user.learning_language_to_id)
            word_for_translate = words["word_for_translate"]
            in_favorite = await get_user_favorite_words(session, word_for_translate.id, user.id)
            response = QuizResponseService.create_random_word_response(word_for_translate, words["other_words"],
                                                                       in_favorite)
            return response

    async def get_random_words(self, language_from_id: int, language_to_id: int) -> dict:
        async with self.session as session:
            word_for_translate = await get_random_word_for_translate(session, language_from_id)
            words = await get_random_words(session, language_to_id, word_for_translate.id)

            add_word_for_translate_to_other_words(words, word_for_translate)
            shuffle_random_words(words)
            return {"other_words": words, "word_for_translate": word_for_translate}

    async def get_match_words(self, telegram_id: int):
        async with self.session as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            words = await get_random_words_for_match(session, user.learning_language_from_id)
            words_list = [{"id": w.id, "name": w.name} for w in words]
            translation_words_list = [{"id": w.translation.id, "name": w.translation.name} for w in words]
            shuffle_random_words(words_list)
            shuffle_random_words(translation_words_list)

            response = QuizResponseService.create_match_words_response(words_list, translation_words_list)
            return response


class FavoriteWordService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_random_favorite_word(self, telegram_id: int):
        async with self.session as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            random_user_favorite_word = await get_random_user_favorite_word(session, user.id)
            other_words = await get_random_words(session, user.learning_language_to_id,
                                                 random_user_favorite_word.id)

            add_word_for_translate_to_other_words(other_words, random_user_favorite_word)
            shuffle_random_words(other_words)

            response = QuizResponseService.create_random_word_response(random_user_favorite_word, other_words,
                                                                       in_favorite=True)
            return response


class SentenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_random_sentence(self, telegram_id: int):
        async with self.session as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            language_to_id = user.learning_language_to_id
            random_sentence_for_translate = await get_random_sentence_for_translate(session,
                                                                                    user.learning_language_from_id)

            words_for_sentence = delete_punctuation(random_sentence_for_translate.translation.name).split()
            random_words_for_sentence = await get_random_words_for_sentence(session, language_to_id, words_for_sentence)

            words_for_sentence.extend(random_words_for_sentence)
            shuffle_random_words(words_for_sentence)

            response = QuizResponseService.create_random_sentence_response(random_sentence_for_translate,
                                                                           words_for_sentence)
            return response


class QuizAnswerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_answer(self, word_for_translate_id: uuid.UUID, user_word_id: uuid.UUID):
        async with self.session as session:
            word = await get_translation_words(session, word_for_translate_id)
            return user_word_id == word.id

    async def check_sentence_answer(self, sentence_id: uuid.UUID, user_words: list[str] = Query(...), ):
        async with self.session as session:
            sentence = await get_sentence_translation(session, sentence_id)
            return delete_punctuation(sentence.name).lower() == " ".join(user_words).lower()


class QuizResponseService:

    @staticmethod
    def create_random_word_response(word_for_translate: WordInfo, words: List[WordInfo],
                                    in_favorite: bool = None) -> RandomWordResponse:
        response = RandomWordResponse(
            type="random_word",
            word_for_translate=WordInfo(**word_for_translate.__dict__),
            other_words=[WordInfo(**word.__dict__) for word in words],
            in_favorite=True if in_favorite else False
        )
        return response

    @staticmethod
    def create_random_sentence_response(random_sentence_for_translate: SentenceInfo, words_for_sentence: List[str]) -> RandomSentenceResponse:
        response = RandomSentenceResponse(
            type="random_sentence",
            sentence_for_translate=SentenceInfo(**random_sentence_for_translate.__dict__),
            words_for_sentence=words_for_sentence
        )
        return response

    @staticmethod
    def create_match_words_response(words_list: List[dict], translation_words_list: List[dict]) -> MatchWordsResponse:
        response = MatchWordsResponse(type="match_words", words=[WordInfo(**word) for word in words_list],
                                      translation_words=[WordInfo(**word) for word in translation_words_list])
        return response
