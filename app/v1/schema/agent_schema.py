"""
Agent Request/Response Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Message model"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    user_id: Optional[str] = Field(None, description="User ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is LangGraph?",
                "conversation_id": "conv_123",
                "user_id": "user_456"
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    conversation_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentState(BaseModel):
    """Agent state model"""
    messages: List[Message]
    current_step: str
    context: Dict[str, Any] = Field(default_factory=dict)
    iteration: int = 0


class ConversationHistory(BaseModel):
    """Conversation history model"""
    conversation_id: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime


class AgentStatus(BaseModel):
    """Agent status model"""
    status: str
    current_step: Optional[str] = None
    iterations: int = 0
    metadata: Optional[Dict[str, Any]] = None