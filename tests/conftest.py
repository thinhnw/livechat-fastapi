import pytest
import aioredis
from typing import AsyncGenerator
from fastapi import status
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorGridFSBucket,
)
from app import oauth2, schemas, utils
from app.config import settings
from app.database import get_db, get_fs
from app.main import app
from httpx import ASGITransport, AsyncClient

from app.redis import get_redis


password = "Foobar1!"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def testdb() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_testdb]

    await client.drop_database(settings.mongo_testdb)
    return db


@pytest.fixture
async def testfs(testdb) -> AsyncGenerator[AsyncIOMotorGridFSBucket, None]:
    return AsyncIOMotorGridFSBucket(testdb)

@pytest.fixture
async def testredis():
    redis = await aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        password=settings.redis_password,
        decode_responses=True,
    )
    try:
        yield redis
    finally:
        await redis.close()


@pytest.fixture()
async def client(testdb, testfs, testredis):
    def override_get_db():
        return testdb

    def override_get_fs():
        return testfs
    
    def override_get_redis():
        return testredis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_fs] = override_get_fs
    app.dependency_overrides[get_redis] = override_get_redis

    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    app.dependency_overrides = {}


@pytest.fixture
async def sample_users(testdb):
    async def _sample_users_data(count=1):
        users_data = []
        for i in range(count):
            users_data.append(
                {
                    "email": f"user_{i}@foobar.com",
                    "password_hash": utils.hash("Foobar1!"),
                    "display_name": f"User {i}",
                }
            )
        await testdb.users.insert_many(users_data)
        return await testdb.users.find().to_list(length=count)

    return _sample_users_data


@pytest.fixture
async def access_tokens():
    async def _access_tokens(users):
        result = []
        for user in users:
            result.append(
                await oauth2.create_access_token(data={"email": user["email"]})
            )
        return result

    return _access_tokens


@pytest.fixture
async def authorized_client(client, sample_users, access_tokens):
    user = (await sample_users(1))[0]
    access_token = (await access_tokens([user]))[0]
    client.headers = {**client.headers, "Authorization": f"Bearer {access_token}"}
    return {"client": client, "current_user": user, "access_token": access_token}


@pytest.fixture
async def get_direct_chat_room(testdb):
    async def _direct_chat_room(user0, user1):
        res = await testdb.chat_rooms.insert_one(
            {
                "type": "direct",
                "user_ids": [str(user0["_id"]), str(user1["_id"])],
            }
        )
        return await testdb.chat_rooms.find_one({"_id": res.inserted_id})

    return _direct_chat_room