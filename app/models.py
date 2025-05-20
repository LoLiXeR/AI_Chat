from pydantic import BaseModel, Field, ConfigDict 
import datetime
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
from typing import Optional




class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

# ...
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    user_message: str
    ai_response: str
    model_used: str
    timestamp: datetime
    model_config = ConfigDict(protected_namespaces=())

class HistoryItem(BaseModel):
    id: int
    user_message: str
    ai_response: str
    model_used: str
    timestamp: datetime
    model_config = ConfigDict(protected_namespaces=())