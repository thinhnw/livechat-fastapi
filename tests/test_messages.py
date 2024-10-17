import pytest
from fastapi import status


@pytest.mark.anyio
async def test_create_message(
    client, testdb, sample_users, access_tokens, get_direct_chat_room
):
    users = await sample_users(2)
    access_tokens = await access_tokens(users)
    direct_chat_room = await get_direct_chat_room(users[0], users[1])

    client.headers = {"Authorization": f"Bearer {access_tokens[0]}"}
    response = await client.post(
        "/messages",
        json={"content": "hello", "chat_room_id": str(direct_chat_room["_id"])},
    )

    assert response.status_code == status.HTTP_201_CREATED

    message = response.json()
    assert message.get("content") == "hello"
    assert message.get("chat_room_id") == str(direct_chat_room["_id"])
    assert message.get("sender_id") == str(users[0]["_id"])
    assert "created_at" in message
