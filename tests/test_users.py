import pytest
from fastapi import status


@pytest.mark.anyio
async def test_change_avatar(client, sample_user, sample_user_token):
    file_path = "tests/sample_avatar.jpeg"
    print(sample_user_token[0])
    with open(file_path, "rb") as f:
        response = await client.put(
            f"/users/{sample_user.get('id')}/avatar",
            headers={"Authorization": f"Bearer {sample_user_token[0]}"},
            files={"file": f},
        )
    assert response.status_code == status.HTTP_200_OK

    file_id = response.json().get("file_id")

    user = await client.get(
        f"/auth/me", headers={"Authorization": f"Bearer {sample_user_token[0]}"}
    )
    assert user.status_code == status.HTTP_200_OK
    assert user.json().get("avatar_file_id") == file_id
