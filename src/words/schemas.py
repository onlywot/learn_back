import uuid

from pydantic import BaseModel, model_validator, UUID4, ConfigDict
from src.constants import AvailableLanguages
from src.quizzes.constants import AvailablePartOfSpeech, AvailableWordLevel


class BaseTranslationSchema(BaseModel):
    translation_from_language: AvailableLanguages
    translation_to_language: AvailableLanguages
    level: AvailableWordLevel

    @model_validator(mode="before")
    def check_different_languages(cls, values):
        if values['translation_from_language'] == values['translation_to_language']:
            raise ValueError("Языки не могут быть одинаковыми")
        return values


class WordSchema(BaseTranslationSchema):
    word_to_translate: str
    translation_word: str
    part_of_speech: AvailablePartOfSpeech

    @model_validator(mode="before")
    def check_different_words(cls, values):
        if values["word_to_translate"] == values["translation_word"]:
            raise ValueError("Слова должны отличаться друг от друга")
        return values


class SentenceSchema(BaseTranslationSchema):
    sentence_to_translate: str
    translation_sentence: str

    @model_validator(mode="before")
    def check_different_sentences(cls, values):
        if values['sentence_to_translate'] == values['translation_sentence']:
            raise ValueError("Предложения должны отличаться друг от друга")
        return values


class WordInfo(BaseModel):
    id: UUID4
    name: str
    model_config = ConfigDict(from_attributes=True)


class SentenceInfo(BaseModel):
    id: UUID4
    name: str
