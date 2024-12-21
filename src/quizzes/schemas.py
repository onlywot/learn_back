import uuid
from typing import List, Optional

from pydantic import BaseModel

from src.words.schemas import SentenceInfo, WordInfo


class UserFavoriteWord(BaseModel):
    telegram_id: int
    word_id: uuid.UUID


class RandomWordResponse(BaseModel):
    type: str
    word_for_translate: WordInfo
    other_words: List[WordInfo]
    in_favorite: Optional[bool]


class RandomSentenceResponse(BaseModel):
    type: str
    sentence_for_translate: SentenceInfo
    words_for_sentence: List[str]


class MatchWordsResponse(BaseModel):
    type: str
    words: List[WordInfo]
    translation_words: List[WordInfo]
