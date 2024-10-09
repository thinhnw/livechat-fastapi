import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone

from app.settings import settings
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def create_access_token(data: dict) -> str:

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_token_ttl)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError as e:
        raise credentials_exception

    user = await db.users.find_one({"email": payload.email})
    if user is None:
        raise credentials_exception
    return user
