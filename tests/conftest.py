import pytest
from httpx import AsyncClient, ASGITransport
from pytest_asyncio import is_async_test
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from src import Base
from src.database import TEST_DATABASE_URL, get_async_session
from src.main import app

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
    app.dependency_overrides[get_async_session] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://127.0.0.1:1234/"
    ) as ac:
        yield ac
