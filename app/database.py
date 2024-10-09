from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.settings import settings


client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_database]


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    return db
