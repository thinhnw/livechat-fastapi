from datetime import datetime, timedelta, timezone
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
    assert message.get("user_id") == str(users[0]["_id"])
    assert "created_at" in message


@pytest.mark.anyio
async def test_get_messages_in_direct_chat_room(
    client, testdb, sample_users, access_tokens
):
    users = await sample_users(2)
    access_tokens = await access_tokens(users)
    direct_chat_room = await testdb.chat_rooms.insert_one(
        {
            "type": "direct",
            "user_ids": [users[0]["_id"], users[1]["_id"]],
        }
    )
    base_time = datetime.now(timezone.utc) 
    await testdb.messages.insert_many([
        {
            "content": f"Message {i}",
            "chat_room_id": direct_chat_room.inserted_id,
            "user_id": users[i % 2]["_id"],
            "created_at": base_time + timedelta(seconds=i),
        }
        for i in range(10)
    ])

    client.headers = {"Authorization": f"Bearer {access_tokens[0]}"}

    response = await client.get(
        f"/messages?chat_room_id={str(direct_chat_room.inserted_id)}"
    )
    assert response.status_code == status.HTTP_200_OK
    messages = response.json().get("messages")
    assert len(messages) == 10
    assert messages[0].get("content") == "Message 9"

    response = await client.get(
        f"/messages?chat_room_id={str(direct_chat_room.inserted_id)}&page=5&page_size=2"
    )
    assert response.status_code == status.HTTP_200_OK
    messages = response.json().get("messages")
    assert len(messages) == 2
    assert messages[0].get("content") == "Message 1"
    assert messages[1].get("content") == "Message 0"

@pytest.mark.anyio
async def test_get_messages_in_chat_room_unauthorized(
    client, testdb, sample_users, access_tokens
):
    users = await sample_users(3)
    access_tokens = await access_tokens(users)
    direct_chat_room = await testdb.chat_rooms.insert_one(
        {
            "type": "direct",
            "user_ids": [users[0]["_id"], users[1]["_id"]],
        }
    )

    await testdb.messages.insert_many(
        [
            {
                "content": f"Message {i}",
                "chat_room_id": direct_chat_room.inserted_id,
                "user_id": users[i % 2]["_id"],
                "created_at": datetime.now(timezone.utc),
            }
            for i in range(2)
        ]
    )

    client.headers = {"Authorization": f"Bearer {access_tokens[2]}"}

    response = await client.get(
        f"/messages?chat_room_id={str(direct_chat_room.inserted_id)}"
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
