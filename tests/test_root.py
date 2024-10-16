from fastapi.testclient import TestClient
import pytest
from app.main import app


@pytest.mark.anyio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_db(client):
    response = await client.get("/db")
    assert response.status_code == 200
