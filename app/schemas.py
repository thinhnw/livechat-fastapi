from enum import Enum
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator


class BaseModelWithId(BaseModel):
    id: str = Field(..., alias="_id")

    @field_validator("id", mode="before")
    def convert_objectid_to_str(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModelWithId):
    email: EmailStr


class ChatRoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class ChatRoom(BaseModelWithId):
    name: str
    type: ChatRoomTypeEnum


class ChatRoomCreate(BaseModel):
    name: str
    type: ChatRoomTypeEnum


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None
