from enum import Enum
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator



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

    @field_validator('id', 'avatar_file_id', mode='before')
    def validate_object_id(cls, value):
        if isinstance(value, ObjectId):
            return str(value)  # Convert to string if it's an ObjectId
        return value

class UserDisplayResponse(BaseModel):
    display_name: str 


class ChatRoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class Token(BaseModel):
    access_token: str
    token_type: str

