"""
Supabase Database Connection
"""
import logging
from supabase import create_client, Client
from .config import settings

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance
    
    Returns:
        Client: Supabase client instance
    """
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    return supabase


def check_schema_exists(supabase: Client) -> bool:
    """
    Check if required database schema exists
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        bool: True if schema exists, False otherwise
    """
    required_tables = [
        'tour_packages',
        'bookings',
        'package_embeddings',
        'otp_verifications',
        'payments',
        'chat_history'
    ]
    
    try:
        for table in required_tables:
            try:
                # Try to query each table with limit 0 to check existence
                supabase.table(table).select("*").limit(0).execute()
            except Exception as e:
                logger.warning(f"Table '{table}' does not exist or is not accessible: {str(e)}")
                return False
        
        logger.info("All required database tables exist")
        return True
        
    except Exception as e:
        logger.error(f"Error checking schema: {str(e)}")
        return False


def print_migration_instructions():
    """
    Print instructions for running database migrations
    """
    instructions = """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                    DATABASE SCHEMA NOT INITIALIZED                       ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    
    Please initialize your database schema by following these steps:
    
    1. Go to your Supabase Dashboard: https://supabase.com/dashboard
    2. Navigate to your project
    3. Click on "SQL Editor" in the left sidebar
    4. Open the migration file: Backend/migrations/init_schema.sql
    5. Copy the entire SQL content
    6. Paste it into the Supabase SQL Editor
    7. Click "Run" to execute the migration
    
    Required tables:
    - tour_packages
    - bookings
    - package_embeddings
    - otp_verifications
    - payments
    - chat_history
    
    Required functions:
    - search_tour_packages()
    - create_tour_booking()
    - verify_and_confirm_booking()
    
    After running the migration, restart this application.
    ════════════════════════════════════════════════════════════════════════════
    """
    print(instructions)


# Global Supabase client instance
supabase_client = get_supabase_client()

# Check schema on module import
if not check_schema_exists(supabase_client):
    logger.warning("Database schema is not initialized!")
    print_migration_instructions()
