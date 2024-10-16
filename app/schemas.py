from enum import Enum
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return ObjectId(v)
        raise ValueError(f'Invalid ObjectId: {v}')
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserChangeDisplayName(BaseModel):
    display_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    email: EmailStr
    avatar_file_id: ObjectId = Field(default_factory=ObjectId)
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ChatRoomTypeEnum(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class ChatRoomResponse(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId)
    name: str
    type: ChatRoomTypeEnum
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ChatRoomCreate(BaseModel):
    name: str
    type: ChatRoomTypeEnum


class Token(BaseModel):
    access_token: str
    token_type: str

