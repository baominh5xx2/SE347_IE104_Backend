"""
Database Schema Initialization
Automatically creates required tables, indexes, and functions if they don't exist
"""
import logging
from typing import Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)

# Schema definitions
SCHEMA_SQL = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users table (assuming it exists, just add index)
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);

-- Tour Packages Table
CREATE TABLE IF NOT EXISTS tour_packages (
    package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_name VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    available_slots INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    image_urls TEXT,
    cuisine VARCHAR(500),
    suitable_for VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for tour_packages
CREATE INDEX IF NOT EXISTS idx_packages_destination ON tour_packages(destination);
CREATE INDEX IF NOT EXISTS idx_packages_dates ON tour_packages(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_packages_active ON tour_packages(is_active);

-- Package Embeddings Table
CREATE TABLE IF NOT EXISTS package_embeddings (
    package_id UUID PRIMARY KEY REFERENCES tour_packages(package_id) ON DELETE CASCADE,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON package_embeddings 
    USING ivfflat (embedding vector_cosine_ops);

-- OTP Verifications Table
CREATE TABLE IF NOT EXISTS otp_verifications (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    otp_code VARCHAR(6) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    attempts INTEGER DEFAULT 0 CHECK (attempts >= 0)
);

CREATE INDEX IF NOT EXISTS idx_otp_booking ON otp_verifications(booking_id);
CREATE INDEX IF NOT EXISTS idx_otp_expires ON otp_verifications(expires_at);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN ('momo', 'vnpay', 'zalopay', 'bank_transfer')),
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    transaction_id VARCHAR(255),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);

-- Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    intent VARCHAR(100),
    entities JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_gin ON chat_history USING GIN(entities);
"""

FUNCTIONS_SQL = """
-- OTP Expiry Trigger Function
CREATE OR REPLACE FUNCTION set_otp_expiry()
RETURNS TRIGGER AS $$
BEGIN
    NEW.expires_at = NEW.created_at + INTERVAL '5 minutes';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_otp_expiry') THEN
        CREATE TRIGGER trigger_otp_expiry
            BEFORE INSERT ON otp_verifications
            FOR EACH ROW EXECUTE FUNCTION set_otp_expiry();
    END IF;
END;
$$;

-- Search Tour Packages Function
CREATE OR REPLACE FUNCTION search_tour_packages(
    search_destination VARCHAR DEFAULT '',
    min_budget DECIMAL DEFAULT 0,
    max_budget DECIMAL DEFAULT 999999999,
    start_after_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    package_id UUID, package_name VARCHAR, destination VARCHAR, 
    price DECIMAL, duration_days INTEGER, available_slots INTEGER,
    start_date DATE, image_urls TEXT, cuisine VARCHAR, suitable_for VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tp.package_id, tp.package_name, tp.destination, tp.price,
        tp.duration_days, tp.available_slots, tp.start_date, tp.image_urls, tp.cuisine, tp.suitable_for
    FROM tour_packages tp
    WHERE tp.is_active = TRUE
        AND tp.available_slots > 0
        AND tp.price BETWEEN min_budget AND max_budget
        AND tp.start_date >= start_after_date
        AND (LOWER(tp.destination) LIKE LOWER('%' || search_destination || '%') OR search_destination = '')
    ORDER BY 
        CASE WHEN LOWER(tp.destination) LIKE LOWER(search_destination || '%') THEN 0 ELSE 1 END,
        tp.price ASC;
END;
$$ LANGUAGE plpgsql;

-- Create Tour Booking Function
CREATE OR REPLACE FUNCTION create_tour_booking(
    user_phone VARCHAR, user_name VARCHAR, contact_phone VARCHAR,
    package_id_param UUID, num_people INTEGER, special_requests TEXT DEFAULT NULL
)
RETURNS TABLE (booking_id UUID, total_amount DECIMAL, otp_code VARCHAR) AS $$
DECLARE
    user_id_val UUID;
    pkg_price DECIMAL;
    new_booking_id UUID;
    otp_generated VARCHAR(6);
    calc_amount DECIMAL;
BEGIN
    -- Get/create user
    SELECT user_id INTO user_id_val FROM users WHERE phone_number = user_phone;
    IF NOT FOUND THEN
        INSERT INTO users (phone_number, full_name) VALUES (user_phone, user_name) RETURNING user_id INTO user_id_val;
    END IF;
    
    -- Check package
    SELECT price INTO pkg_price FROM tour_packages WHERE package_id = package_id_param AND is_active = TRUE AND available_slots >= num_people;
    IF NOT FOUND THEN RAISE EXCEPTION 'Package not available'; END IF;
    
    calc_amount := pkg_price * num_people;
    
    -- Create booking
    INSERT INTO bookings (user_id, package_id, number_of_people, total_amount, contact_name, contact_phone, special_requests, status)
    VALUES (user_id_val, package_id_param, num_people, calc_amount, user_name, contact_phone, special_requests, 'otp_sent')
    RETURNING bookings.booking_id INTO new_booking_id;
    
    -- Generate OTP
    otp_generated := LPAD((RANDOM() * 999999)::INTEGER::TEXT, 6, '0');
    
    -- Create OTP
    INSERT INTO otp_verifications (booking_id, user_id, otp_code, phone_number) 
    VALUES (new_booking_id, user_id_val, otp_generated, user_phone);
    
    -- Update slots
    UPDATE tour_packages SET available_slots = available_slots - num_people WHERE package_id = package_id_param;
    
    RETURN QUERY SELECT new_booking_id, calc_amount, otp_generated;
END;
$$ LANGUAGE plpgsql;

-- Verify and Confirm Booking Function
CREATE OR REPLACE FUNCTION verify_and_confirm_booking(booking_id_param UUID, otp_input VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    otp_rec RECORD;
BEGIN
    SELECT * INTO otp_rec FROM otp_verifications 
    WHERE booking_id = booking_id_param AND otp_code = otp_input 
        AND expires_at > CURRENT_TIMESTAMP AND is_verified = FALSE AND attempts < 3;
    
    IF NOT FOUND THEN
        UPDATE otp_verifications SET attempts = attempts + 1 WHERE booking_id = booking_id_param;
        RETURN FALSE;
    END IF;
    
    UPDATE otp_verifications SET is_verified = TRUE, verified_at = CURRENT_TIMESTAMP WHERE booking_id = booking_id_param;
    UPDATE bookings SET status = 'confirmed' WHERE booking_id = booking_id_param;
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
"""


async def init_database_schema(supabase: Client) -> Dict[str, Any]:
    """
    Initialize database schema by creating tables, indexes, and functions if they don't exist
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        Dict containing initialization results
    """
    results = {
        "success": False,
        "schema_created": False,
        "functions_created": False,
        "errors": []
    }
    
    try:
        logger.info("Starting database schema initialization...")
        
        # Execute schema creation
        logger.info("Creating tables and indexes...")
        try:
            # Supabase client doesn't directly support raw SQL execution
            # We need to use RPC or the PostgREST API
            # For now, we'll use the rpc method to execute SQL
            schema_result = supabase.rpc('exec_sql', {'sql': SCHEMA_SQL}).execute()
            results["schema_created"] = True
            logger.info("Schema tables and indexes created successfully")
        except Exception as e:
            error_msg = f"Error creating schema: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Execute functions creation
        logger.info("Creating database functions...")
        try:
            functions_result = supabase.rpc('exec_sql', {'sql': FUNCTIONS_SQL}).execute()
            results["functions_created"] = True
            logger.info("Database functions created successfully")
        except Exception as e:
            error_msg = f"Error creating functions: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        if results["schema_created"] and results["functions_created"]:
            results["success"] = True
            logger.info("Database initialization completed successfully")
        
    except Exception as e:
        error_msg = f"Unexpected error during database initialization: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    return results


def check_table_exists(supabase: Client, table_name: str) -> bool:
    """
    Check if a table exists in the database
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        # Try to query the table with a limit of 0
        result = supabase.table(table_name).select("*").limit(0).execute()
        return True
    except Exception as e:
        logger.debug(f"Table {table_name} does not exist or is not accessible: {str(e)}")
        return False


async def ensure_schema_exists(supabase: Client) -> None:
    """
    Ensure that the database schema exists, initialize if not
    
    Args:
        supabase: Supabase client instance
    """
    # Check if key tables exist
    tables_to_check = ['tour_packages', 'package_embeddings', 'otp_verifications', 'payments', 'chat_history']
    
    all_exist = all(check_table_exists(supabase, table) for table in tables_to_check)
    
    if not all_exist:
        logger.info("Some tables are missing, initializing database schema...")
        result = await init_database_schema(supabase)
        
        if not result["success"]:
            logger.warning(f"Database initialization completed with warnings: {result['errors']}")
        else:
            logger.info("Database schema is ready")
    else:
        logger.info("Database schema already exists")

