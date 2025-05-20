# app/database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
import datetime
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class ChatMessage(Base):
    __tablename__ = "chat_messages" 

    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(String)
    ai_response = Column(String)
    model_used = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow) # Автоматическая установка времени

#хеширование
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_db_and_tables():
    Base.metadata.create_all(engine)
