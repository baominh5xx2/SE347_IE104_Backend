"""Schema package initialization"""
from .auth_schema import (
    RegisterRequest,
    LoginRequest,
    VerifyTokenRequest,
    RegisterResponse,
    LoginResponse,
    VerifyTokenResponse,
    GoogleLoginRequest,
    GoogleCallbackRequest,
    GoogleAuthURLResponse
)
from .agent_schema import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    AgentState,
    ConversationHistory,
    AgentStatus
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "VerifyTokenRequest",
    "RegisterResponse",
    "LoginResponse",
    "VerifyTokenResponse",
    "GoogleLoginRequest",
    "GoogleCallbackRequest",
    "GoogleAuthURLResponse",
    "ChatRequest",
    "ChatResponse",
    "Message",
    "MessageRole",
    "AgentState",
    "ConversationHistory",
    "AgentStatus"
]
