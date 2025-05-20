# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openai import OpenAI
import os
import datetime
import httpx
from datetime import timedelta
from database import SessionLocal, engine, ChatMessage, User, create_db_and_tables
from models import ChatRequest, ChatResponse, HistoryItem, UserCreate, UserResponse, UserLogin, Token 

from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES 
)


app = FastAPI(
    title="AI Chat Backend",
    description="Backend.",
    version="1.2.0" 
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    print("Database tables created/checked.")

# Зависимость
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


custom_httpx_client = httpx.Client(proxies=None, timeout=30.0)

AITUNNEL_API_KEY = os.getenv("AITUNNEL_API_KEY")
if not AITUNNEL_API_KEY:
    raise ValueError("AITUNNEL_API_KEY environment variable not set. Please set it in your docker-compose.yml.")

client = OpenAI(
    api_key=AITUNNEL_API_KEY,
    base_url="https://api.aitunnel.ru/v1/",
    http_client=custom_httpx_client
)


MODEL_MAPPING = {
    "deepseek": "deepseek-r1",
    "gpt-4": "gpt-4o",
    "gemini-flash": "gemini-2.0-flash-001",
}

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the AI Chat Backend!"}


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Регистрирует нового пользователя с уникальным именем пользователя и хешированным паролем.
    """
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким именем уже зарегистрирован"
        )

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать пользователя из-за ошибки базы данных."
        )

    return UserResponse(id=new_user.id, username=new_user.username)



@app.post("/login", response_model=Token, summary="Log in a user and get JWT token")
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Аутентифицирует пользователя по имени пользователя и паролю и выдает JWT токен.
    """
    db_user = db.query(User).filter(User.username == user_data.username).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(user_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    #JWT токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username}, # 'sub' - стандартное поле для субъекта (имя пользователя)
        expires_delta=access_token_expires
    )
    print(f"Пользователь {db_user.username} успешно вошел в систему. Токен выдан.")
    return {"access_token": access_token, "token_type": "bearer"}


#Отправка сообщения
@app.post("/chat", response_model=ChatResponse, summary="Send a message to a selected AI model (Requires Auth)")
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user), # <-- Добавлена зависимость для авторизации
    db: Session = Depends(get_db)
):
    """
    Отправляет сообщение выбранной AI модели и сохраняет историю в базе данных.
    Требует JWT-токена для авторизации.
    """

    print(f"Пользователь {current_user.username} отправляет сообщение AI.")

    model_name_for_api = MODEL_MAPPING.get(request.model)

    if not model_name_for_api:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI model selected."
        )

    try:
        print(f"Sending message to model: {model_name_for_api}")
        chat_result = client.chat.completions.create(
            messages=[{"role": "user", "content": request.message}],
            model=model_name_for_api,
            max_tokens=50000,
        )
        ai_response_content = chat_result.choices[0].message.content

        # Сохраняем
        new_message = ChatMessage(
            user_message=request.message,
            ai_response=ai_response_content,
            model_used=request.model,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        return ChatResponse(
            user_message=request.message,
            ai_response=ai_response_content,
            model_used=request.model,
            timestamp=new_message.timestamp
        )

    except Exception as e:
        print(f"Error during AI chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while communicating with the AI model: {e}"
        )

#Получение истории чатов
@app.get("/history", response_model=list[HistoryItem], summary="Retrieve chat history (Requires Auth)")
async def get_chat_history(
    current_user: User = Depends(get_current_user), # <-- Добавлена зависимость для авторизации
    db: Session = Depends(get_db)
):
    """
    Получает всю историю чатов из базы данных.
    Требует JWT-токена для авторизации.
    В дальнейшем может быть доработано для показа истории только текущего пользователя.
    """
    print(f"Пользователь {current_user.username} запрашивает историю чатов.")

    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp).all()
    return [
        HistoryItem(
            id=msg.id,
            user_message=msg.user_message,
            ai_response=msg.ai_response,
            model_used=msg.model_used,
            timestamp=msg.timestamp
        ) for msg in messages
    ]