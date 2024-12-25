import pytest
from httpx import AsyncClient, ASGITransport
from pytest_asyncio import is_async_test
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from src import Base
from src.database import TEST_DATABASE_URL, get_async_session
from src.dependencies import check_hash
from src.main import app
from src.models import Word, TranslationWord, Language, Sentence, TranslationSentence, User

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
AsyncTestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def connection_test():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield AsyncTestingSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(connection_test):
    async with connection_test() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session) -> TestClient:
    app.dependency_overrides[check_hash] = lambda: None
    app.dependency_overrides[get_async_session] = lambda: db_session
    async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test/"
    ) as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
async def populate_bd(connection_test):
    async with connection_test() as session:

        # add languages
        language_en = Language(language="English")
        session.add(language_en)
        language_ru = Language(language="Russian")
        session.add(language_ru)
        await session.flush()

        # add words
        for i in range(10):
            # word
            word = Word(name=f"string{i}", language_id=1, part_of_speech="noun", level="A1")
            session.add(word)
            await session.flush()
            translation_word = TranslationWord(word_id=word.id, from_language_id=2, to_language_id=1, name=f"строка{i}")
            session.add(translation_word)

        # add sentence
        sentence = Sentence(name=f"Hello, word", language_id=1, level="A1")
        session.add(sentence)
        await session.flush()
        translation_sentence = TranslationSentence(
            name="Привет, мир", sentence_id=sentence.id, from_language_id=1, to_language_id=2
        )
        session.add(translation_sentence)

        # add user
        user = User(
            telegram_id=11,
            first_name="first_name",
            photo_url="photo_url",
            username="username",
            learning_language_from_id=2,
            learning_language_to_id=1,
        )
        session.add(user)

        # commit all changes
        await session.commit()
