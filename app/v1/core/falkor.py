"""
FalkorDB Connection - Simple connection from .env
"""
from falkordb import FalkorDB
from app.v1.core.config import settings


def get_falkor_connection():
    """
    Get FalkorDB connection from environment variables
    
    Returns:
        FalkorDB client instance
    """
    try:
        client = FalkorDB(
            host=settings.FALKORDB_HOST,
            port=settings.FALKORDB_PORT,
            username=settings.FALKORDB_USERNAME,
            password=settings.FALKORDB_PASSWORD,
            ssl=settings.FALKORDB_SSL
        )
        
        graph = client.select_graph(settings.FALKORDB_DATABASE)
        
        return graph
    except Exception as e:
        print(f"FalkorDB connection error: {e}")
        return None


# Singleton instance
falkor_graph = get_falkor_connection()
