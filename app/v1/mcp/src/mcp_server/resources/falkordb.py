"""
FalkorDB Resource - Initialize FalkorDB connection
"""
from fastmcp import FastMCP
import logging

from src.mcp_server.utils.falkordb_client import FalkorDBClient
from src.mcp_server.core.config import settings

logger = logging.getLogger(__name__)


def register_falkordb_resources(mcp: FastMCP):
    """
    Initialize FalkorDB connection when MCP server starts
    
    This initializes the FalkorDB connection using the singleton client,
    which will be reused by tools that need it.
    
    Args:
        mcp (FastMCP): FastMCP instance (for future resource registration if needed)
    """
    try:
        # Initialize FalkorDB connection
        logger.info("🔄 Initializing FalkorDB connection...")
        logger.info(f"   Host: {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}")
        logger.info(f"   Database: {settings.FALKORDB_DATABASE}")
        
        # Initialize connection using singleton client
        client = FalkorDBClient()
        graph = client.get_graph()
        
        if graph:
            logger.info(f"✅ FalkorDB connection initialized successfully")
            logger.info(f"   Graph database ready: {settings.FALKORDB_DATABASE}")
        else:
            logger.warning("⚠️ FalkorDB connection failed - graph is None")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize FalkorDB connection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - allow server to start even if FalkorDB is unavailable
        logger.warning("⚠️ MCP server will continue without FalkorDB connection")

