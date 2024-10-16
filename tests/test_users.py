import pytest

valid_email = "foo@bar.com"
valid_password = "Foobar1!"

invalid_email = "foobar"
invalid_password = "foobar"

@pytest.mark.anyio
@pytest.mark.parametrize("email, password, status_code", [
    (valid_email, valid_password, 200),
    (valid_email, invalid_password, 400),
    (invalid_email, valid_password, 422),
    (None, invalid_password, 422),
    (valid_email, None, 422),
])
async def test_user_registration(client, email, password, status_code):
    response = await client.post("/auth/register", json={"email": email, "password": password})
    print(response.json())
    assert response.status_code == status_code