from enum import Enum
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime, timezone

import pydantic

from app import utils


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserChangeDisplayName(BaseModel):
    display_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    display_name: str
    avatar_file_id: str | None = None

    @field_validator("id", "avatar_file_id", mode="before")
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value

    @pydantic.computed_field
    @property
    def avatar_url(self) -> str:
        return utils.get_avatar_url(self.avatar_file_id, self.display_name)


class UserDisplayResponse(BaseModel):
    display_name: str


class UsersListResponse(BaseModel):
    users: list[UserResponse]


class ChatRoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class DirectChatRoomCreate(BaseModel):
    user_ids: list[str] = Field(..., min_length=2, max_length=2)


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    chat_room_id: str
    user_id: str
    created_at: datetime

    @field_validator("id", "chat_room_id", "user_id", mode="before")
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value

    class Config:
        # This ensures the alias is respected during serialization
        allow_population_by_field_name = True
        # Use alias when serializing to JSON
        json_encoders = {ObjectId: str}


class MessagesListResponse(BaseModel):
    messages: list[MessageResponse]


class Token(BaseModel):
    access_token: str
    token_type: str
