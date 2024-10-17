import pytest
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


@pytest.fixture()
async def client(testdb, testfs):
    def override_get_db():
        return testdb

    def override_get_fs():
        return testfs

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_fs] = override_get_fs

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
            result.append(await oauth2.create_access_token(data={"email": user["email"]}))
        return result

    return _access_tokens
