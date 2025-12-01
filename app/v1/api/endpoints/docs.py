import logging
from fastapi import APIRouter
from typing import Dict, Any

from Backend.app.v1.api import router
@router.get("/docs")
async def get_api_docs():
    """
    Get comprehensive API documentation

    Returns:
        Complete API documentation with all endpoints
    """
    try:
        return {
            "api_version": "v1",
            "base_url": "/api/v1",
            "description": "Tour Booking AI System API",
            "endpoints": {
                "health": {
                    "path": "/health",
                    "methods": ["GET"],
                    "description": "Health check endpoint",
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/",
                            "description": "Basic health check",
                            "response": {
                                "status": "healthy",
                                "timestamp": "2025-11-09T...",
                                "version": "2.1.0"
                            }
                        }
                    ]
                },
                "chat": {
                    "path": "/chat",
                    "methods": ["POST"],
                    "description": "Chat and conversation endpoints",
                    "endpoints": [
                        {
                            "method": "POST",
                            "path": "/",
                            "description": "Send chat message (non-streaming)",
                            "request_body": {
                                "message": "string (required)",
                                "conversation_id": "string (optional)",
                                "user_id": "string (optional)"
                            },
                            "response": {
                                "conversation_id": "string",
                                "message": "string",
                                "metadata": "object",
                                "timestamp": "datetime"
                            }
                        },
                        {
                            "method": "POST",
                            "path": "/stream",
                            "description": "Send chat message with streaming response",
                            "request_body": {
                                "message": "string (required)",
                                "conversation_id": "string (optional)",
                                "user_id": "string (optional)"
                            },
                            "response": "Server-Sent Events (SSE) stream",
                            "events": [
                                {"type": "start", "description": "Conversation started"},
                                {"type": "token", "description": "Streaming token"},
                                {"type": "recommendations", "description": "Tour recommendations"},
                                {"type": "metadata", "description": "Additional metadata"},
                                {"type": "done", "description": "Stream completed"}
                            ]
                        },
                        {
                            "method": "GET",
                            "path": "/conversation/{conversation_id}",
                            "description": "Get conversation history",
                            "parameters": {
                                "conversation_id": "string (path parameter)"
                            },
                            "response": {
                                "conversation_id": "string",
                                "messages": "array of message objects",
                                "created_at": "datetime",
                                "updated_at": "datetime"
                            }
                        },
                        {
                            "method": "DELETE",
                            "path": "/conversation/{conversation_id}",
                            "description": "Delete conversation and history",
                            "parameters": {
                                "conversation_id": "string (path parameter)"
                            },
                            "response": {
                                "message": "string",
                                "conversation_id": "string"
                            }
                        }
                    ]
                },
                "auth": {
                    "path": "/auth",
                    "methods": ["POST", "GET"],
                    "description": "Authentication endpoints",
                    "endpoints": [
                        {
                            "method": "POST",
                            "path": "/login",
                            "description": "User login",
                            "request_body": {
                                "email": "string",
                                "password": "string"
                            }
                        },
                        {
                            "method": "POST",
                            "path": "/register",
                            "description": "User registration",
                            "request_body": {
                                "email": "string",
                                "password": "string",
                                "name": "string"
                            }
                        },
                        {
                            "method": "GET",
                            "path": "/me",
                            "description": "Get current user info",
                            "headers": {
                                "Authorization": "Bearer {token}"
                            }
                        }
                    ]
                },
                "tour_packages": {
                    "path": "/tour-packages",
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "description": "Tour package management",
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/",
                            "description": "Get all tour packages with filtering",
                            "query_params": {
                                "is_active": "boolean (optional)",
                                "destination": "string (optional)",
                                "limit": "integer (optional)",
                                "offset": "integer (optional)"
                            },
                            "response": {
                                "data": "array of tour packages",
                                "total": "integer",
                                "limit": "integer",
                                "offset": "integer"
                            }
                        },
                        {
                            "method": "GET",
                            "path": "/{package_id}",
                            "description": "Get specific tour package",
                            "parameters": {
                                "package_id": "UUID (path parameter)"
                            }
                        },
                        {
                            "method": "POST",
                            "path": "/",
                            "description": "Create new tour package",
                            "request_body": "TourPackageCreate object"
                        },
                        {
                            "method": "PUT",
                            "path": "/{package_id}",
                            "description": "Update tour package",
                            "parameters": {
                                "package_id": "UUID (path parameter)"
                            },
                            "request_body": "TourPackageUpdate object"
                        },
                        {
                            "method": "DELETE",
                            "path": "/{package_id}",
                            "description": "Delete tour package",
                            "parameters": {
                                "package_id": "UUID (path parameter)"
                            }
                        }
                    ]
                },
                "tours": {
                    "path": "/tours",
                    "methods": ["GET"],
                    "description": "Simplified tour endpoints",
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/recommended",
                            "description": "Get recommended tours",
                            "query_params": {
                                "limit": "integer (optional, default: 6)"
                            },
                            "response": "array of tour objects"
                        }
                    ]
                }
            },
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer {token}",
                "description": "Include Bearer token in Authorization header for protected endpoints"
            },
            "response_format": {
                "success": {
                    "status": "success",
                    "data": "response data",
                    "message": "optional message"
                },
                "error": {
                    "status": "error",
                    "message": "error message",
                    "code": "error code"
                }
            },
            "streaming": {
                "description": "Chat streaming uses Server-Sent Events (SSE)",
                "content_type": "text/event-stream",
                "events": [
                    "start: Conversation initialization",
                    "token: Individual token chunks",
                    "recommendations: Tour recommendations data",
                    "metadata: Additional response metadata",
                    "done: Stream completion"
                ]
            },
            "external_services": {
                "mem0": "Long-term conversation memory",
                "supabase": "Tour package database",
                "openai": "LLM for agent intelligence",
                "mcp_server": "Tool integration via Model Context Protocol"
            },
            "generated_at": "2025-11-09T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting API docs: {str(e)}")
        return {
            "error": str(e),
            "message": "Failed to generate API documentation"
        }
