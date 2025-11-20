"""
Supabase Resource - Initialize Supabase connection
"""
from fastmcp import FastMCP
from supabase import create_client, Client
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Singleton Supabase client
_supabase_client: Client = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton"""
    global _supabase_client
    
    if _supabase_client is None:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"✅ Supabase client created for URL: {SUPABASE_URL[:30]}...")
    
    return _supabase_client


def register_supabase_resources(mcp: FastMCP):
    """
    Initialize Supabase connection when MCP server starts
    
    This initializes the Supabase connection using the singleton client,
    which will be reused by tools that need it.
    
    Args:
        mcp (FastMCP): FastMCP instance (for future resource registration if needed)
    """
    try:
        logger.info("🔄 Initializing Supabase connection...")
        
        # Initialize connection using singleton client
        client = get_supabase_client()
        
        if client:
            logger.info(f"✅ Supabase connection initialized successfully")
        else:
            logger.warning("⚠️ Supabase connection failed - client is None")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase connection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - allow server to start even if Supabase is unavailable
        logger.warning("⚠️ MCP server will continue without Supabase connection")
