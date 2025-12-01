"""Core package initialization"""
from .config import settings, Settings

# Import BackendClient only if it exists (for backward compatibility)
try:
    from .client import BackendClient
    __all__ = ["settings", "Settings", "BackendClient"]
except ImportError:
    __all__ = ["settings", "Settings"]
