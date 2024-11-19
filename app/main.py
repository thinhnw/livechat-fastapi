from contextlib import asynccontextmanager
from io import BytesIO
import json
from bson import ObjectId, json_util
import uvicorn
from fastapi import (
    FastAPI,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


from app import oauth2, schemas, utils
from app.connection_manager import ConnectionManager
from app.database import get_db, get_fs
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    yield
    # on shutdown


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:5173",
    "https://livechat-react.pages.dev"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello You"}


@app.get("/db")
async def db_healthcheck(db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        db = await get_db()
        response = await db.command("ping")
        if response:
            return {"status": "MongoDB is running"}
        else:
            raise HTTPException(status_code=500, detail="MongoDB did not respond")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error connecting to MongoDB: {str(e)}"
        )


@app.post("/auth/register")
async def register(
    payload: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)
):

    existed = await db.users.find_one({"email": payload.email})
    if existed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    if not utils.is_strong_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain at "
            "least one uppercase letter, one lowercase letter, one digit, "
            "and one special character",
        )
    res = await db.users.insert_one(
        {
            "email": payload.email,
            "password_hash": utils.hash(payload.password),
            "display_name": "New User",
        }
    )
    return {"user_id": str(res.inserted_id)}


@app.post("/auth/login")
async def login(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> schemas.Token:
    content_type = request.headers.get("content-type")

    if content_type == "application/x-www-form-urlencoded":
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
    elif content_type == "application/json":
        payload = await request.json()
        username = payload.get("email")
        password = payload.get("password")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    user = await db.users.find_one({"email": username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
        )
    if not utils.verify(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
        )
    access_token = await oauth2.create_access_token(data={"email": user["email"]})

    return schemas.Token(access_token=access_token, token_type="Bearer")


@app.get("/auth/me")
async def me(
    user=Depends(oauth2.get_current_user),
) -> schemas.UserResponse:
    return schemas.UserResponse(**user)


@app.put("/users/me/display_name")
async def change_user_display_name(
    payload: schemas.UserChangeDisplayName,
    db=Depends(get_db),
    user=Depends(oauth2.get_current_user),
):
    updated_result = await db.users.update_one(
        {"_id": user.get("_id")}, {"$set": {"display_name": payload.display_name}}
    )
    if updated_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    return {"message": "Display name updated successfully"}


@app.put("/users/me/avatar")
async def change_user_avatar(
    db=Depends(get_db),
    fs=Depends(get_fs),
    user=Depends(oauth2.get_current_user),
    file: UploadFile = File(...),
):
    file_id = await fs.upload_from_stream(
        file.filename, file.file, metadata={"content_type": file.content_type}
    )
    updated_result = await db.users.update_one(
        {"_id": user.get("_id")}, {"$set": {"avatar_file_id": file_id}}
    )
    if updated_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    return {"file_id": str(file_id)}


@app.get("/users")
async def search_users(
    search: str = None, db=Depends(get_db)
) -> schemas.UsersListResponse:
    users = await db.users.find(
        {"email": {"$regex": f"^{search}", "$options": "i"}}
    ).to_list(length=10)
    return {"users": [schemas.UserResponse(**user) for user in users]}


@app.get("/users/{id}")
async def get_user(id: str, db=Depends(get_db)) -> schemas.UserDisplayResponse:
    user = await db.users.find_one({"_id": ObjectId(id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.UserDisplayResponse(display_name=user.get("display_name"))


@app.get("/images/{id}")
async def show_image(id: str, fs=Depends(get_fs)):
    grid_out = await fs.open_download_stream(ObjectId(id))
    image_bytes = await grid_out.read()
    return StreamingResponse(BytesIO(image_bytes), media_type="image/jpeg")


@app.post("/chat_rooms/direct", status_code=status.HTTP_201_CREATED)
async def create_direct_chat_room(
    payload: schemas.DirectChatRoomCreate,
    db=Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
) -> schemas.ChatRoomResponse:
    if str(current_user.get("_id")) not in payload.user_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    user_ids = [ObjectId(payload.user_ids[0]), ObjectId(payload.user_ids[1])]
    pipeline = [
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {
                            "$setIsSubset": [user_ids, {"$ifNull": ["$user_ids", []]}]
                        },  # Check if all my_user_ids are in user_ids
                        {
                            "$eq": [len(user_ids), {"$size": "$user_ids"}]
                        },  # Ensure sizes are equal
                    ]
                }
            }
        }
    ]

    existing_chat = await db.chat_rooms.aggregate(pipeline).to_list(length=None)
    if len(existing_chat) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Chat room already exists"
        )
    res = await db.chat_rooms.insert_one({"type": "direct", "user_ids": user_ids})

    chat_partner_id = (
        payload.user_ids[0]
        if payload.user_ids[1] == current_user.get("_id")
        else payload.user_ids[1]
    )
    chat_partner = await db.users.find_one({"_id": ObjectId(chat_partner_id)})
    response = await db.chat_rooms.find_one({"_id": res.inserted_id})
    return schemas.ChatRoomResponse(
        **response,
        name=chat_partner.get("display_name"),
        avatar_url=utils.get_avatar_url(
            chat_partner.get("avatar_file_id"), chat_partner.get("display_name")
        ),
    )


@app.get("/chat_rooms/direct")
async def get_direct_chat_room(
    partner_id: str, db=Depends(get_db), current_user=Depends(oauth2.get_current_user)
) -> schemas.ChatRoomResponse:
    user_ids = [ObjectId(partner_id), ObjectId(current_user["_id"])]
    pipeline = [
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {
                            "$setIsSubset": [user_ids, {"$ifNull": ["$user_ids", []]}]
                        },  # Check if all my_user_ids are in user_ids
                        {
                            "$eq": [len(user_ids), {"$size": "$user_ids"}]
                        },  # Ensure sizes are equal
                    ]
                }
            }
        }
    ]

    chat_rooms = await db.chat_rooms.aggregate(pipeline).to_list(length=None)
    if len(chat_rooms) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found"
        )
    partner = await db.users.find_one({"_id": ObjectId(partner_id)})
    name = partner.get("display_name")
    avatar_url = utils.get_avatar_url(partner.get("avatar_file_id"), name)
    return schemas.ChatRoomResponse(**chat_rooms[0], name=name, avatar_url=avatar_url)


@app.get("/chat_rooms/{id}")
async def get_chat_room(
    id: str, db=Depends(get_db), current_user=Depends(oauth2.get_current_user)
) -> schemas.ChatRoomResponse:
    chat_room = await db.chat_rooms.find_one({"_id": ObjectId(id)})
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.get("_id") not in chat_room.get("user_ids"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    if chat_room.get("type") == "direct":
        partner_id = (
            chat_room.get("user_ids")[0]
            if chat_room.get("user_ids")[1] == current_user.get("_id")
            else chat_room.get("user_ids")[1]
        )
        partner = await db.users.find_one({"_id": ObjectId(partner_id)})
        name = partner.get("display_name")
        avatar_url = utils.get_avatar_url(partner.get("avatar_file_id"), name)
        return schemas.ChatRoomResponse(**chat_room, name=name, avatar_url=avatar_url)
    return schemas.ChatRoomResponse(**chat_room)


@app.get("/chat_rooms")
async def get_chat_rooms(
    db=Depends(get_db), current_user=Depends(oauth2.get_current_user)
) -> schemas.ChatRoomsListResponse:
    chat_rooms = []
    # query direct, group rieng
    pipeline = [
        {"$match": {"type": "direct"}},
        {"$match": {"user_ids": current_user.get("_id")}},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_ids",
                "foreignField": "_id",
                "as": "users",
            }
        },
    ]
    async for chat_room in db.chat_rooms.aggregate(pipeline):
        chat_room["name"] = (
            chat_room["users"][1].get("display_name")
            if chat_room["users"][0].get("_id") == current_user.get("_id")
            else chat_room["users"][0].get("display_name")
        )
        avatar_file_id = (
            chat_room["users"][1].get("avatar_file_id")
            if chat_room["users"][0].get("_id") == current_user.get("_id")
            else chat_room["users"][0].get("avatar_file_id")
        )
        chat_room["avatar_url"] = utils.get_avatar_url(
            avatar_file_id, chat_room["name"]
        )
        chat_rooms.append(chat_room)

    return schemas.ChatRoomsListResponse(chat_rooms=chat_rooms)


@app.post("/messages", status_code=status.HTTP_201_CREATED)
async def post_message(
    payload: schemas.MessageCreate,
    db=Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
) -> schemas.MessageResponse:
    chat_room = await db.chat_rooms.find_one({"_id": ObjectId(payload.chat_room_id)})
    if current_user.get("_id") not in chat_room.get("user_ids"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    res = await db.messages.insert_one(
        {
            **payload.model_dump(),
            "chat_room_id": ObjectId(payload.chat_room_id),
            "user_id": current_user.get("_id"),
        }
    )

    message = await db.messages.find_one({"_id": res.inserted_id})
    return schemas.MessageResponse(**message)


@app.get("/messages")
async def get_messages(
    chat_room_id: str,
    page: int = 1,
    page_size: int = 25,
    db=Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
) -> schemas.MessagesListResponse:
    chat_room = await db.chat_rooms.find_one({"_id": ObjectId(chat_room_id)})
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.get("_id") not in chat_room.get("user_ids"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
        )
    skip = (page - 1) * page_size
    messages = await db.messages.aggregate(
        [
            {
                "$match": {"chat_room_id": ObjectId(chat_room_id)}
            },  # Filter messages by chat room
            {"$sort": {"created_at": -1}},  # Sort by timestamp in descending order
            {"$skip": skip},  # Skip the first (page - 1) * page_size messages
            {"$limit": page_size},  # Limit the number of results to page_size
        ]
    ).to_list(length=page_size)
    return schemas.MessagesListResponse(messages=messages)


# exclude for prod later
@app.post("/scripts/save_image")
async def save_image(fs=Depends(get_fs)):
    with open("tests/sample_avatar.jpeg", "rb") as f:
        file_id = await fs.upload_from_stream(
            "sample_avatar.jpeg", f, metadata={"content_type": "image/jpeg"}
        )
    return str(file_id)


@app.post("/scripts/test_db")
async def test_db(db=Depends(get_db)):
    res = await db.users.find().to_list(length=10)
    return res


manager = ConnectionManager()


@app.websocket("/ws/chat_rooms/{chat_room_id}")
async def websocket_endpoint(
    websocket: WebSocket, chat_room_id: str, db=Depends(get_db)
):
    channel_id = f"chat_room_{chat_room_id}"
    await manager.connect(websocket, channel_id)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            if data["type"] == "auth":
                current_user = await oauth2.get_current_user(data["token"], db)
                print(current_user)
            elif data["type"] == "message":
                message = data["message"]
                chat_room = await db.chat_rooms.find_one(
                    {"_id": ObjectId(message.get("chat_room_id"))}
                )
                if current_user.get("_id") not in chat_room.get("user_ids"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
                    )
                res = await db.messages.insert_one(
                    {
                        "content": message.get("content"),
                        "chat_room_id": ObjectId(message.get("chat_room_id")),
                        "user_id": current_user.get("_id"),
                        "created_at": datetime.now(timezone.utc),
                    }
                )

                message = await db.messages.find_one({"_id": res.inserted_id})
                print(message)
                await manager.broadcast(
                    json_util.dumps(
                        {
                            "type": "message",
                            "message": schemas.MessageResponse(**message).model_dump(by_alias=True),
                        }
                    ),
                    channel_id,
                )
    except WebSocketDisconnect:
        print("Disconnected")
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            print("Unauthorized")
            await websocket.close()
    finally:
        manager.disconnect(websocket, channel_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
