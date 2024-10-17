import pytest
from fastapi import status


@pytest.mark.anyio
async def test_create_direct_chat_room(client, testdb, sample_users, access_tokens):
    users = await sample_users(2)
    access_tokens = await access_tokens(users)

    client.headers = {"Authorization": f"Bearer {access_tokens[0]}"}
    response = await client.post(
        "/chat_rooms/direct",
        json={"users": [str(users[0]["_id"]), str(users[1]["_id"])]},
    )
    assert response.status_code == status.HTTP_201_CREATED

    chat_room = response.json()
    assert chat_room.get("type") == "direct"
    assert chat_room.get("user_ids") == [str(users[0]["_id"]), str(users[1]["_id"])]
    
    