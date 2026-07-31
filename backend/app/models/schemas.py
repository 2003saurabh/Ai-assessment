from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ToolInfo(BaseModel):
    tool_used: str  # "rag", "sql", "both", "fallback"
    sql_query: Optional[str] = None
    citations: Optional[list[str]] = None


class ChatResponse(BaseModel):
    answer: str
    tool_info: ToolInfo
