from typing import AsyncGenerator
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from .config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, TEST_DB_USER, TEST_DB_PASS, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME


DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
TEST_DATABASE_URL = f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASS}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

redis_pool = redis.ConnectionPool.from_url("redis://redis:6379", max_connections=10)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)
