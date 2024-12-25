import pytest
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Language


@pytest.mark.asyncio
async def test_create_language(client, db_session: AsyncSession):
    language_en = Language(language="English")
    db_session.add(language_en)
    language_ru = Language(language="Russian")
    db_session.add(language_ru)
    await db_session.commit()
    result = await db_session.execute(select(func.count(Language.id)))
    languages_count = result.scalar()
    assert languages_count == 2


@pytest.mark.asyncio
async def test_success_create_user(client):
    data = {
        "telegram_id": 0,
        "learning_language_from_id": 1,
        "learning_language_to_id": 2,
        "photo_url": "string",
        "username": "string",
        "first_name": "string"
    }
    response = await client.post("/user", json=data)
    assert response.status_code == 200
    response = response.json()
    assert response["telegram_id"] == 0
    assert response["learning_language_from_id"] == 1
    assert response["learning_language_to_id"] == 2


@pytest.mark.asyncio
async def test_get_user_from_db(client, db_session: AsyncSession):
    result = await db_session.execute(select(User))
    user = result.scalar()
    assert user.id == 1
    assert user.telegram_id == 0
    assert user.learning_language_from_id == 1
    assert user.learning_language_to_id == 2


@pytest.mark.asyncio
async def test_get_user_data(client):
    data = {"page": 1, "size": 10}
    response = await client.get("/user", params=data)
    assert response.status_code == 200
    response = response.json()
    assert response["users_count"] == 1
    assert len(response["users"]) == 1
    assert response["users"][0]["id"] == 1
    assert response["users"][0]["telegram_id"] == 0
    assert response["users"][0]["learning_language_from_id"] == 1
    assert response["users"][0]["learning_language_to_id"] == 2


@pytest.mark.asyncio
async def test_change_user_learn_language(client):
    data = {
        "telegram_id": 0,
        "learning_language_from_id": 2,
        "learning_language_to_id": 1
    }
    response = await client.patch("/user/change-user-language", json=data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_update_user_data_from_db(client, db_session: AsyncSession):
    result = await db_session.execute(select(User))
    user = result.scalar()
    assert user.id == 1
    assert user.telegram_id == 0
    assert user.learning_language_from_id == 2
    assert user.learning_language_to_id == 1


@pytest.mark.asyncio
async def test_get_update_user_data(client):
    data = {"page": 1, "size": 10}
    response = await client.get("/user", params=data)
    assert response.status_code == 200
    response = response.json()
    assert response["users"][0]["telegram_id"] == 0
    assert response["users"][0]["learning_language_from_id"] == 2
    assert response["users"][0]["learning_language_to_id"] == 1


@pytest.mark.asyncio
async def test_create_user_with_same_languages(client):
    data = {
        "telegram_id": 1,
        "learning_language_from_id": 1,
        "learning_language_to_id": 1,
        "photo_url": "string",
        "username": "string",
        "first_name": "string"
    }
    response = await client.post("/user", json=data)
    assert response.status_code == 422
    response = response.json()
    assert response["detail"][0]["msg"] == "Value error, Языки обучения не могут быть одинаковыми."


@pytest.mark.asyncio
async def test_create_user_with_wrong_languages(client):
    data = {
        "telegram_id": 1,
        "learning_language_from_id": 22,
        "learning_language_to_id": 1,
        "photo_url": "string",
        "username": "string",
        "first_name": "string"
    }
    response = await client.post("/user", json=data)
    assert response.status_code == 422
    response = response.json()
    assert response["detail"][0]["type"] == "enum"


@pytest.mark.asyncio
async def test_create_user_with_same_id(client):
    data = {
        "telegram_id": 0,
        "learning_language_from_id": 2,
        "learning_language_to_id": 1,
        "photo_url": "string",
        "username": "string",
        "first_name": "string"
    }
    response = await client.post("/user", json=data)
    assert response.status_code == 203
    response = response.json()
    assert response["detail"] == "Пользователь уже зарегистрирован"
