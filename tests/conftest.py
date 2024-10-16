import pytest
from typing import AsyncGenerator
from fastapi import status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app import schemas, utils
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
async def testdb() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_testdb]

    await client.drop_database(settings.mongo_testdb)
    return db


@pytest.fixture()
def client(testdb):
    async def override_get_db():
        return testdb

    app.dependency_overrides[get_db] = override_get_db

    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    app.dependency_overrides = {}


@pytest.fixture
async def sample_user(testdb):
    await testdb.users.insert_one(
        {
            "email": valid_email,
            "password_hash": utils.hash(valid_password),
        }
    )
    return await testdb.users.find_one({"email": valid_email})


def get_access_token(email, password):

    @pytest.fixture
    async def login(client):
        response = await client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == status.HTTP_200_OK
        return (
            response.json()["access_token"],
            response.json()["token_type"],
        )

    return login


sample_user_token = get_access_token(valid_email, valid_password)
