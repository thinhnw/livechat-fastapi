from contextlib import asynccontextmanager
from io import BytesIO
from bson import ObjectId
import uvicorn
from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import oauth2, schemas, utils
from app.database import get_db, get_fs
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
        }
    )
    return {"user_id": str(res.inserted_id)}


@app.post("/auth/login")
async def login(
    payload: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> schemas.Token:
    user = await db.users.find_one({"email": payload.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
        )
    if not utils.verify(payload.password, user["password_hash"]):
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

    response = await db.chat_rooms.find_one({"_id": res.inserted_id})
    return schemas.ChatRoomResponse(**response)


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
