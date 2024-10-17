import pytest
from fastapi import status


@pytest.mark.anyio
async def test_change_avatar(authorized_client, testdb):
    file_path = "tests/sample_avatar.jpeg"
    with open(file_path, "rb") as f:
        response = await authorized_client["client"].put(
            f"/users/me/avatar",
            files={"file": f},
        )
    assert response.status_code == status.HTTP_200_OK

    file_id = response.json().get("file_id")
    user = await testdb.users.find_one(
        {"email": authorized_client["current_user"].get("email")}
    )
    assert str(user.get("avatar_file_id")) == file_id


# @pytest.mark.anyio
# async def test_change_avatar_unauthorized(client, sample_user, sample_user_token):
#     pass

# @pytest.mark.anyio
# async def test_change_avatar_invalid_file(client, sample_user, sample_user_token):
#     pass


@pytest.mark.anyio
async def test_change_display_name(authorized_client, testdb):
    new_display_name = "Bar Foo"
    response = await authorized_client["client"].put(
        f"/users/me/display_name",
        json={"display_name": new_display_name},
    )
    assert response.status_code == status.HTTP_200_OK

    user = await testdb.users.find_one(
        {"email": authorized_client["current_user"].get("email")}
    )
    assert user.get("display_name") == new_display_name


@pytest.mark.anyio
async def test_show_user(client, sample_users):
    user = (await sample_users(1))[0]
    response = await client.get(f"/users/{user.get('_id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("display_name") == user.get("display_name")

