from pydantic import BaseModel
from typing import Optional, Any


# ─── Chat Models ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    validated: bool = False
    source: Optional[str] = "supabase"
    method: Optional[str] = "sql-comparison"
    sql_query: Optional[str] = None
    data_count: Optional[int] = 0


class Message(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class Session(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    user_id: Optional[str] = None


# ─── Auth Models ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserSession(BaseModel):
    user_id: str
    username: str
    role: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


# ─── Earthquake Models ────────────────────────────────────────────────────────

class EarthquakeInput(BaseModel):
    id: str
    place: Optional[str] = None
    date: Optional[str] = None
    month: Optional[int] = None
    month_name: Optional[str] = None
    year: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    magnitude: Optional[float] = None
    depth: Optional[float] = None
    depth_category: Optional[str] = None
    time: Optional[str] = None
