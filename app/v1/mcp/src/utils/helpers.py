"""
Utility functions for MCP server
"""
import logging
from typing import Any, Dict
import json


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("mcp_server")


def format_response(
    success: bool,
    data: Any = None,
    error: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Format a standardized response
    
    Args:
        success: Whether the operation was successful
        data: Response data
        error: Error message if any
        **kwargs: Additional fields
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "success": success,
        **kwargs
    }
    
    if data is not None:
        response["data"] = data
    
    if error is not None:
        response["error"] = error
    
    return response


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """
    Safely serialize object to JSON
    
    Args:
        obj: Object to serialize
        indent: JSON indentation
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        return json.dumps({"error": f"Serialization failed: {str(e)}"})


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
