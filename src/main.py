import random
import uuid
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import and_
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi.middleware.cors import CORSMiddleware

from .models import Word, User, Exam, ExamQuestion
from .schemas import UserCreate, UserInfo, WordResponse, WordInfo
from .utils import get_random_words
from .database import get_async_session
from src.exam.router import router as exam_router

app = FastAPI(docs_url=None, title='Learn API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/user")
async def create_user(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    existing_user = await session.scalar(select(User).where(User.telegram_id == user_data.telegram_id))
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже зарегистрирован")
    new_user = User(telegram_id=user_data.telegram_id)
    session.add(new_user)

    try:
        await session.commit()
        await session.refresh(new_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при сохранении пользователя")

    return {"response": f"Пользователь с id {new_user.id} успешно создан"}


@app.get("/user", response_model=List[UserInfo])
async def get_users_list(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User))
    users_list = result.scalars().all()
    return users_list


@app.get("/user/{user_id}", response_model=UserInfo)
async def get_user_info(telegram_id: int, session: AsyncSession = Depends(get_async_session)):
    user_data = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user_data is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user_data


@app.get("/get-word", response_model=WordResponse)
async def get_word(language: str, session: AsyncSession = Depends(get_async_session)):
    word_for_translate, random_words = await get_random_words(session)

    if language == "eng":
        response_data = WordResponse(
            word_for_translate=WordInfo(id=word_for_translate.id, name=word_for_translate.name),
            other_words=[WordInfo(id=word.translation.id, name=word.translation.name) for word in random_words]
        )

    elif language == "ru":
        response_data = WordResponse(
            word_for_translate=WordInfo(id=word_for_translate.id, name=word_for_translate.translation.name),
            other_words=[WordInfo(id=word.translation.id, name=word.name) for word in random_words]
        )
    else:
        raise HTTPException(status_code=404, detail="Язык не найден")

    return response_data


@app.get("/check-answer", response_model=Optional[bool])
async def check_answer(
        word_for_translate_id: uuid.UUID,
        user_choice_word_id: uuid.UUID,
        session: AsyncSession = Depends(get_async_session),
):
    query = select(Word).where(Word.id == word_for_translate_id)
    word_for_translate = await session.scalar(query)
    if word_for_translate is None:
        raise HTTPException(status_code=404, detail=f"Слово с id {word_for_translate_id} не найдено")
    if word_for_translate.translation_id == user_choice_word_id:
        return True
    return False

app.include_router(exam_router)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )
