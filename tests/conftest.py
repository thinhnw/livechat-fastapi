from typing import AsyncGenerator
import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app import utils
from app.config import settings
from app.database import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient

valid_email = "foo@bar.com"
valid_password = "Foobar1!"

invalid_email = "foobar"
invalid_password = "foobar"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    client = AsyncIOMotorClient(settings.mongo_uri)
    test_db = client[settings.mongo_testdb]

    await client.drop_database(settings.mongo_testdb)
    return test_db


@pytest.fixture()
def client(test_db):
    async def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    app.dependency_overrides = {}


@pytest.fixture
async def user_setup(test_db):
    await test_db.users.insert_one(
        {
            "email": valid_email,
            "password_hash": utils.hash(valid_password),
        }
    )
