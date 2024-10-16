import pytest
from fastapi import status
from .conftest import valid_email, valid_password, invalid_email, invalid_password


@pytest.mark.anyio
@pytest.mark.parametrize(
    "email, password, status_code",
    [
        (valid_email, valid_password, status.HTTP_200_OK),
        (valid_email, invalid_password, status.HTTP_400_BAD_REQUEST),
        (invalid_email, valid_password, status.HTTP_422_UNPROCESSABLE_ENTITY),
        (None, invalid_password, status.HTTP_422_UNPROCESSABLE_ENTITY),
        (valid_email, None, status.HTTP_422_UNPROCESSABLE_ENTITY),
    ],
)
async def test_registration(client, testdb, email, password, status_code):
    response = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == status_code
    user = await testdb.users.find_one({"email": email})
    assert user if status_code == status.HTTP_200_OK else not user


@pytest.mark.anyio
async def test_registration_with_existing_email(client, sample_user):
    response = await client.post(
        "/auth/register", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.anyio
@pytest.mark.parametrize(
    "email, password, status_code",
    [
        (valid_email, valid_password, 200),
        (valid_email + "typo", invalid_password, 401),
        (valid_email, invalid_password, 401),
        (invalid_email, valid_password, 422),
        (None, invalid_password, 422),
        (valid_email, None, 422),
    ],
)
async def test_login(client, sample_user, email, password, status_code):
    response = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        assert "access_token" in response.json()


@pytest.mark.anyio
async def test_me(client, sample_user, sample_user_token):
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {sample_user_token[0]}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("email") == sample_user.get("email")

