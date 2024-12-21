from aiogram.utils.web_app import check_webapp_signature
from fastapi import HTTPException

from src.config import BOT_TOKEN
from src.database import get_redis
from src.words.service import CacheRedisService


def get_redis_connect():
    return CacheRedisService(get_redis())


def check_hash(init_data: str) -> None:
    if not check_webapp_signature(BOT_TOKEN, init_data):
        raise HTTPException(status_code=403, detail="Don't have permission")
