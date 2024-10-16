from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from app.config import settings


client = AsyncIOMotorClient(settings.mongo_uri)
main_db = client[settings.mongo_maindb]


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    return main_db

async def get_fs() -> AsyncGenerator[AsyncIOMotorGridFSBucket, None]:
    return AsyncIOMotorGridFSBucket(main_db)
