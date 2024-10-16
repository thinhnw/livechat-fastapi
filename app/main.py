from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, status

from app import oauth2, schemas, utils
from app.database import get_db, get_fs
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from gridfs import GridFS


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
        {"email": payload.email, "password_hash": utils.hash(payload.password)}
    )
    return {"user_id": str(res.inserted_id)}


@app.post("/auth/login")
async def login(
    payload: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)
) -> schemas.Token:
    user = await db.users.find_one({"email": payload.email})
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
) -> schemas.UserResponse:
    return user


@app.put("/users/{id}/avatar")
async def change_display_name(
    db=Depends(get_db),
    fs=Depends(get_fs),
    user=Depends(oauth2.get_current_user),
    file: UploadFile = File(...),
):
    file_id = await fs.upload_from_stream(file.filename, file.file)
    updated_result = await db.users.update_one(
        {"_id": user.get("_id")}, {"$set": {"avatar_file_id": file_id}}
    )
    if updated_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    print(str(file_id))
    return {"file_id": str(file_id)}


@app.post("/chat_rooms")
async def create_chat_room(
    payload: schemas.ChatRoomCreate,
    db=Depends(get_db),
    user=Depends(oauth2.get_current_user),
):
    chat_room = await db.chat_rooms.insert_one(
        {**payload.model_dump(), "users": [user.get("email")]}
    )
    return str(chat_room.inserted_id)


@app.get("/chat_rooms")
async def get_chat_rooms(
    db=Depends(get_db),
    user=Depends(oauth2.get_current_user),
) -> list[schemas.ChatRoomResponse]:
    print(user.get("email"))
    chat_rooms = await db.chat_rooms.find(
        {"users": {"$in": [user.get("email")]}}
    ).to_list()
    return chat_rooms


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
