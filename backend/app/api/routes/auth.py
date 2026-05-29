from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_user, hash_password, verify_password, create_access_token, decode_access_token
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(prefix='/auth', tags=['auth']) 

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    
    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters")
        return v
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    
class UserResponse(BaseModel):
    id: str
    email : str
    
    class Config:
        form_attributes = True
        
        
@router.post('/register', response_model=UserResponse, status_code=201)
async def register_user(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email== body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email = body.email,
        hashed_password = hash_password(body.password) 
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post('/login', response_model=TokenResponse, status_code=201)
async def login_user(form_data : OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    
    access_token = create_access_token(data={'sub': user.id})
    return TokenResponse(access_token=access_token)

@router.get('/me', response_model=UserResponse)
async def get_user(current_user: User = Depends(get_current_user)):
    return current_user
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    