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
    username: EmailStr
    password: str


class UserResponse(BaseModelWithId):
    pass

class ChatRoom(BaseModelWithId):
    name: str
