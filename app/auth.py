# app/auth.py

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session 

from database import SessionLocal, User 
from passlib.context import CryptContext
import os 


SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-please-change-this-in-production")
ALGORITHM = "HS256" # Алгоритм хеширования JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 5000 


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login") 


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Хеширует пароль."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие открытого пароля хешированному."""
    return pwd_context.verify(plain_password, hashed_password)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT токен доступа.
    data: словарь с данными для включения в полезную нагрузку токена (например, {"sub": "username"}).
    expires_delta: timedelta, указывающий время жизни токена.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) 
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)] # Получаем сессию
):
    """
    Зависимость для получения текущего аутентифицированного пользователя из JWT токена.
    Используется для защиты эндпоинтов.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub") 
        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first() # Находим пользователя в БД по имени из токена
    if user is None:
        raise credentials_exception
    return user # Возвращаем объект пользователя, который будет доступен в эндпоинте