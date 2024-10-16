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
async def test_registration(client, test_db, email, password, status_code):
    response = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == status_code
    user = await test_db.users.find_one({"email": email})
    assert user if status_code == status.HTTP_200_OK else not user


@pytest.mark.anyio
async def test_registration_with_existing_email(client, user_setup):
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
async def test_login(client, user_setup, email, password, status_code):
    response = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        assert "access_token" in response.json()
