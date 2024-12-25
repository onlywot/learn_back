import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import TranslationWord


@pytest.mark.asyncio
async def test_quiz_random_word(client, db_session: AsyncSession):
    response = await client.get("/quiz/random-word", params={"telegram_id": 11})
    assert response.status_code == 200
    response = response.json()
    assert len(response["other_words"]) == 3


@pytest.mark.asyncio
async def test_quiz_check_answer_for_random_word(client, db_session: AsyncSession):
    result = await db_session.execute(select(TranslationWord))
    word_data = result.scalar()
    translation_word_id = word_data.id
    word_id = word_data.word_id
    params = {"word_for_translate_id": word_id, "user_word_id": translation_word_id}
    response = await client.get("/quiz/check-answer", params=params)
    assert response.status_code == 200
    response = response.json()
    assert response is True
