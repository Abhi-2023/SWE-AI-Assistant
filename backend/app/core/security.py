from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import get_settings
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from app.db.database import get_db
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User

oauth_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(plain_password: str):
    return pwd_context.hash(plain_password[:72])


def verify_password(plain_password: str, hash_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hash_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode['exp'] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def decode_access_token(token: str) -> str:
    try:
        if payload:= jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm]):
            return payload.get('sub')
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired, Please login again"
        ) from e
        
        
async def get_current_user(token : str = Depends(oauth_scheme), db: AsyncSession = Depends(get_db)):
    if payload := decode_access_token(token):
        user_id = payload
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    if user := result.scalar_one_or_none():
        return user
    else:
        raise HTTPException(status_code=401, detail="User not found")
