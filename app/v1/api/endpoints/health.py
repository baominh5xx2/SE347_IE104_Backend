"""
Health Check API Endpoints
"""
import logging
from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Detailed health status check
    
    Returns:
        Health status with component checks
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {}
    }
    
    # Check Supabase connection
    try:
        from ...core.supabase import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            health_status["components"]["supabase"] = {
                "status": "healthy",
                "connected": True
            }
        else:
            health_status["components"]["supabase"] = {
                "status": "unhealthy",
                "connected": False
            }
    except Exception as e:
        health_status["components"]["supabase"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check FalkorDB connection
    try:
        from ...core.falkor import falkor_graph
        if falkor_graph:
            # Test with simple query
            result = falkor_graph.query("RETURN 'OK' as status")
            if result and result.result_set:
                health_status["components"]["falkordb"] = {
                    "status": "healthy",
                    "connected": True
                }
            else:
                health_status["components"]["falkordb"] = {
                    "status": "unhealthy",
                    "connected": False
                }
        else:
            health_status["components"]["falkordb"] = {
                "status": "unhealthy",
                "connected": False
            }
    except Exception as e:
        health_status["components"]["falkordb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Agent System has been removed - skip check
    
    # Overall status
    all_healthy = all(
        comp.get("status") == "healthy" 
        for comp in health_status["components"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/docker-compose
    
    Returns:
        Simple ready/not ready status
    """
    try:
        # Check if critical components are available
        from ...core.supabase import get_supabase_client
        
        # Basic checks
        has_supabase = get_supabase_client() is not None
        
        if has_supabase:
            return {
                "ready": True,
                "status": "ready"
            }
        else:
            return {
                "ready": False,
                "status": "not ready",
                "reason": "Supabase not initialized"
            }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "ready": False,
            "status": "not ready",
            "error": str(e)
        }

