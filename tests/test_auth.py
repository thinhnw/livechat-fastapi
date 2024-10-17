import pytest
from fastapi import status

from app import oauth2
from .conftest import password


@pytest.mark.anyio
async def test_registration_with_valid_credentials(client, testdb):
    email = "foo@bar.com"
    response = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == status.HTTP_200_OK
    user = await testdb.users.find_one({"email": email})
    assert user


@pytest.mark.anyio
async def test_registration_with_existing_email(client, sample_users):
    user = (await sample_users(1))[0]
    response = await client.post(
        "/auth/register", json={"email": user["email"], "password": password}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == "Email already exists"


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_password", ["foo", "12345678", "Abcdefgh1"])
async def test_registration_with_invalid_password(client, invalid_password):
    response = await client.post(
        "/auth/register", json={"email": "foo@bar.com", "password": invalid_password}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == (
        "Password must be at least 8 characters long and contain at "
        "least one uppercase letter, one lowercase letter, one digit, "
        "and one special character"
    )


@pytest.mark.anyio
async def test_login_with_valid_credentials(client, sample_users):
    user = (await sample_users(1))[0]
    response = await client.post(
        "/auth/login", data={"username": user["email"], "password": password}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_with_invalid_credentials(client, sample_users):
    user = (await sample_users(1))[0]
    response = await client.post(
        "/auth/login", data={"username": user["email"], "password": "invalid"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_me(client, sample_users, access_tokens):
    user = (await sample_users(1))[0]
    token = (await access_tokens([user]))[0]
    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("email") == user.get("email")
