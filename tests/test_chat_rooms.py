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


@pytest.mark.anyio
async def test_get_chat_rooms(client, testdb, sample_users, access_tokens):
    users = await sample_users(3)
    access_tokens = await access_tokens(users)

    client.headers = {"Authorization": f"Bearer {access_tokens[0]}"}

    await testdb.chat_rooms.insert_many(
        [
            {
                "type": "direct",
                "user_ids": [users[0]["_id"], users[1]["_id"]],
            },
            {
                "type": "direct",
                "user_ids": [users[0]["_id"], users[2]["_id"]],
            },
            {
                "type": "direct",
                "user_ids": [users[1]["_id"], users[2]["_id"]],
            },
        ]
    )
    response = await client.get("/chat_rooms")
    assert response.status_code == status.HTTP_200_OK 

    chat_rooms = response.json().get("chat_rooms", [])
    assert len(chat_rooms) == 2

    for chat_room in chat_rooms:
        assert chat_room.get("type") == "direct"
        assert "name" in chat_room
        assert chat_room.get("user_ids") in [
            [str(users[0]["_id"]), str(users[1]["_id"])],
            [str(users[0]["_id"]), str(users[2]["_id"])],
        ]
    