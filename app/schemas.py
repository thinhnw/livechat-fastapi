from enum import Enum
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserChangeDisplayName(BaseModel):
    display_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserMeResponse(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    display_name: str
    avatar_file_id: str | None = None

    @field_validator("id", "avatar_file_id", mode="before")
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value


class UserDisplayResponse(BaseModel):
    display_name: str


class ChatRoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class DirectChatRoomCreate(BaseModel):
    users: list[str] = Field(..., min_length=2, max_length=2)


class ChatRoomResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    avatar_url: str
    type: ChatRoomTypeEnum
    user_ids: list[str]

    @field_validator("id", mode="before")
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value

    @field_validator("user_ids", mode="before")
    def validate_user_ids(cls, value):
        result = []
        for user_id in value:
            if isinstance(user_id, ObjectId):
                result.append(str(user_id))
            else:
                result.append(user_id)
        return result

class ChatRoomsListResponse(BaseModel):
    chat_rooms: list[ChatRoomResponse]


class MessageCreate(BaseModel):
    chat_room_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    chat_room_id: str
    sender_id: str
    created_at: datetime

    @field_validator("id", "chat_room_id", "sender_id", mode="before")
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value


class Token(BaseModel):
    access_token: str
    token_type: str
