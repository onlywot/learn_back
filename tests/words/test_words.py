import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models import Word, Sentence, User


@pytest.mark.asyncio
async def test_add_words(client):
    data = {
        "translation_from_language": 2,
        "translation_to_language": 1,
        "level": "A1",
        "word_to_translate": "test",
        "translation_word": "тест",
        "part_of_speech": "noun"
    }
    response = await client.post("/words/add-word", json=data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_words_from_db(db_session: AsyncSession):
    result = await db_session.execute(select(Word).options(joinedload(Word.translation)).where(Word.name == "test"))
    word = result.scalar()
    assert word.name == "test"
    assert word.language_id == 2
    assert word.translation.name == "тест"
    assert word.translation.from_language_id == 2
    assert word.translation.to_language_id == 1


@pytest.mark.asyncio
async def test_add_words_with_same_languages(client):
    data = {
        "translation_from_language": 1,
        "translation_to_language": 1,
        "level": "A1",
        "word_to_translate": "test",
        "translation_word": "тест",
        "part_of_speech": "noun"
    }
    response = await client.post("/words/add-word", json=data)
    assert response.status_code == 422
    response = response.json()
    assert response["detail"][0]["msg"] == "Value error, Языки не могут быть одинаковыми"


@pytest.mark.asyncio
async def test_add_words_with_same_words(client):
    data = {
        "translation_from_language": 1,
        "translation_to_language": 2,
        "level": "A1",
        "word_to_translate": "test",
        "translation_word": "test",
        "part_of_speech": "noun"
    }
    response = await client.post("/words/add-word", json=data)
    assert response.status_code == 422
    response = response.json()
    assert response["detail"][0]["msg"] == "Value error, Слова должны отличаться друг от друга"
