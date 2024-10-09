from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status

from app import oauth2, schemas, utils
from app.database import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase


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


@app.get("/chat_rooms")
async def get_chat_rooms(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[schemas.ChatRoom]:
    chat_rooms = await db.chat_rooms.find().to_list(length=100)
    return chat_rooms


@app.post("/auth/register")
async def register(
    payload: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> str:

    existed = await db.users.find_one({"email": payload.email})
    if existed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )
    res = await db.users.insert_one(
        {"email": payload.email, "hashed_password": utils.hash(payload.password)}
    )
    return str(res.inserted_id)


@app.post("/auth/login")
async def login(
    payload: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)
) -> schemas.Token:
    user = await db.users.find_one({"email": payload.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid Credentials"
        )
    if not utils.verify(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect password"
        )
    access_token = await oauth2.create_access_token(data={"email": user["email"]})

    return schemas.Token(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
