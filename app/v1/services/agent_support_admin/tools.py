"""
Admin Agent Tools
Database query tools for admin agent
"""
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryDatabaseInput(BaseModel):
    """Input schema for query_database tool"""
    sql_query: str = Field(
        description="SQL SELECT query to execute. Must be a valid SELECT statement."
    )
    explanation: str = Field(
        default="",
        description="Brief explanation of what this query does"
    )


def _get_supabase_client():
    """Get Supabase client"""
    from app.v1.core.supabase import get_supabase_client
    return get_supabase_client()


def _execute_admin_query(sql_query: str) -> Dict[str, Any]:
    """
    Execute admin query via Supabase RPC
    
    Args:
        sql_query: SQL SELECT query
        
    Returns:
        Query result as dict
    """
    try:
        supabase = _get_supabase_client()
        
        # Call RPC function
        result = supabase.rpc('admin_execute_query', {
            'query_text': sql_query
        }).execute()
        
        if result.data:
            # Check for error in result
            if isinstance(result.data, dict) and result.data.get('error'):
                return {
                    "success": False,
                    "error": result.data.get('message', 'Unknown error'),
                    "query": sql_query
                }
            
            return {
                "success": True,
                "data": result.data,
                "row_count": len(result.data) if isinstance(result.data, list) else 1,
                "query": sql_query
            }
        else:
            return {
                "success": True,
                "data": [],
                "row_count": 0,
                "query": sql_query
            }
            
    except Exception as e:
        logger.error(f"Error executing admin query: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": sql_query
        }


@tool(args_schema=QueryDatabaseInput)
def query_database(sql_query: str, explanation: str = "") -> Dict[str, Any]:
    """
    Execute a SELECT query on the database.
    
    Available tables:
    - tour_packages: package_id, package_name, destination, price, duration_days, available_slots, start_date, end_date, is_active, created_at
    - bookings: booking_id, package_id, user_id, number_of_people, total_amount, status (pending/confirmed/cancelled/completed), created_at
    - users: user_id, email, full_name, phone_number, role (user/admin), is_active, created_at, last_access_time
    - payments: payment_id, booking_id, user_id, amount, payment_status, payment_method, created_at
    - reviews: review_id, package_id, user_id, rating (1-5), comment, created_at
    - promotions: promotion_id, code, discount_type, discount_value, is_active, start_date, end_date
    
    RULES:
    - Only SELECT queries allowed (no INSERT/UPDATE/DELETE)
    - Always include LIMIT (max 100 recommended)
    - Use aggregate functions: COUNT, SUM, AVG, MAX, MIN
    - Use JOINs when needed to combine data
    
    Example queries:
    - "SELECT COUNT(*) as total FROM bookings WHERE status = 'confirmed'"
    - "SELECT destination, COUNT(*) as cnt FROM tour_packages GROUP BY destination ORDER BY cnt DESC LIMIT 5"
    - "SELECT EXTRACT(MONTH FROM created_at) as month, SUM(total_amount) as revenue FROM bookings GROUP BY month"
    
    Args:
        sql_query: Valid SQL SELECT statement
        explanation: Brief explanation of the query purpose
        
    Returns:
        Query results as JSON with data array
    """
    logger.info(f"🔍 Admin Query: {sql_query[:100]}...")
    
    result = _execute_admin_query(sql_query)
    
    if result["success"]:
        logger.info(f"✅ Query returned {result['row_count']} rows")
    else:
        logger.warning(f"❌ Query failed: {result.get('error')}")
    
    return result


def get_admin_tools() -> List[StructuredTool]:
    """Get all admin tools"""
    return [query_database]

