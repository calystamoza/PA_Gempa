from pydantic import BaseModel
from typing import Optional, Any


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


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
