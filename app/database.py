from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings


client = AsyncIOMotorClient(settings.mongo_uri)
main_db = client[settings.mongo_maindb]


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    return main_db


