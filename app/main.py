from contextlib import asynccontextmanager
from io import BytesIO
from bson import ObjectId
import uvicorn
from fastapi import FastAPI, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware


from app import oauth2, schemas, utils
from app.database import get_db, get_fs
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db = await get_db()
        await db.command("ping")
        print("You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:5173",
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
    await db["healthcheck"].insert_one({"created_at": datetime.now()})
    return {"message": "OK"}


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
) -> schemas.UserMeResponse:
    return user


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
    if str(current_user.get("_id")) not in payload.users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    res = await db.chat_rooms.insert_one(
        {
            "type": "direct",
            "user_ids": [
                ObjectId(payload.users[0]),
                ObjectId(payload.users[1]),
            ],
        }
    )

    chat_partner_id = (
        payload.users[0]
        if payload.users[1] == current_user.get("_id")
        else payload.users[1]
    )
    chat_partner = await db.users.find_one({"_id": ObjectId(chat_partner_id)})
    response = await db.chat_rooms.find_one({"_id": res.inserted_id})
    return schemas.ChatRoomResponse(
        **response,
        name=chat_partner.get("display_name"),
        avatar_url=settings.api_url
        + "/images/"
        + str(chat_partner.get("avatar_file_id")),
    )


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
        if avatar_file_id is not None:
            print("FATAL", avatar_file_id is not None)
            chat_room["avatar_url"] = settings.api_url + "/images/" + avatar_file_id
        else:
            chat_room["avatar_url"] = (
                f"https://ui-avatars.com/api/?name={chat_room['name'].replace(' ', '+')}"
            )
        chat_rooms.append(chat_room)

    return schemas.ChatRoomsListResponse(chat_rooms=chat_rooms)


@app.post("/messages", status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: schemas.MessageCreate,
    db=Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
) -> schemas.MessageResponse:
    res = await db.messages.insert_one(
        {
            **payload.model_dump(),
            "sender_id": current_user.get("_id"),
        }
    )

    message = await db.messages.find_one({"_id": res.inserted_id})
    return schemas.MessageResponse(**message)


# exclude for prod later
@app.post("/scripts/save_image")
async def save_image(fs=Depends(get_fs)):
    with open("tests/sample_avatar.jpeg", "rb") as f:
        file_id = await fs.upload_from_stream(
            "sample_avatar.jpeg", f, metadata={"content_type": "image/jpeg"}
        )
    return str(file_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
