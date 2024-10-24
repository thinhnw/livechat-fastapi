import re
from bson import ObjectId
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def is_strong_password(password):
    # Define a regular expression for a strong password
    regex = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return re.match(regex, password) is not None


def hash(password: str) -> str:
    return pwd_context.hash(password)


def verify(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def get_avatar_url(file_id: ObjectId | str | None, name: str | None) -> str:
    if file_id:
        return f"{settings.api_url}/images/{str(file_id)}"
    return f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}"