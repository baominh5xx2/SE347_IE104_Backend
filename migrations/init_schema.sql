-- ============================================
-- Database Schema Initialization for Tour Booking System
-- Execute this in Supabase SQL Editor
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";


-- ============================================
-- TOUR PACKAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS tour_packages (
    package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_name VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL, -- Đà Lạt, Nha Trang, Phú Quốc...
    description TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    available_slots INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    image_urls TEXT, -- URL hình ảnh phân cách bằng |
    cuisine TEXT, -- Ẩm thực
    suitable_for TEXT, -- Phù hợp cho
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for tour_packages search optimization
CREATE INDEX IF NOT EXISTS idx_packages_destination ON tour_packages(destination);
CREATE INDEX IF NOT EXISTS idx_packages_dates ON tour_packages(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_packages_active ON tour_packages(is_active);

-- Full-text search index for hybrid search optimization
ALTER TABLE tour_packages ADD COLUMN IF NOT EXISTS search_vector tsvector;
CREATE INDEX IF NOT EXISTS idx_packages_search_vector ON tour_packages USING GIN(search_vector);

-- Function to update search_vector automatically
CREATE OR REPLACE FUNCTION update_tour_packages_search_vector() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.package_name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.destination, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update search_vector on insert/update
DROP TRIGGER IF EXISTS trigger_update_tour_packages_search_vector ON tour_packages;
CREATE TRIGGER trigger_update_tour_packages_search_vector
    BEFORE INSERT OR UPDATE ON tour_packages
    FOR EACH ROW
    EXECUTE FUNCTION update_tour_packages_search_vector();

-- Update existing rows
UPDATE tour_packages SET search_vector = 
    setweight(to_tsvector('simple', COALESCE(package_name, '')), 'A') ||
    setweight(to_tsvector('simple', COALESCE(destination, '')), 'B') ||
    setweight(to_tsvector('simple', COALESCE(description, '')), 'C')
WHERE search_vector IS NULL;

-- ============================================
-- BOOKINGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES tour_packages(package_id) ON DELETE CASCADE,
    number_of_people INTEGER NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(15) NOT NULL,
    special_requests TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, otp_sent, confirmed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bookings_package ON bookings(package_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

-- ============================================
-- PACKAGE EMBEDDINGS TABLE (for AI search)
-- ============================================
CREATE TABLE IF NOT EXISTS package_embeddings (
    package_id UUID PRIMARY KEY REFERENCES tour_packages(package_id) ON DELETE CASCADE,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON package_embeddings 
    USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- OTP VERIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS otp_verifications (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
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

-- ============================================
-- OTP AUTO-EXPIRY TRIGGER (5 minutes)
-- ============================================
CREATE OR REPLACE FUNCTION set_otp_expiry()
RETURNS TRIGGER AS $$
BEGIN
    NEW.expires_at = NEW.created_at + INTERVAL '5 minutes';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_otp_expiry ON otp_verifications;
CREATE TRIGGER trigger_otp_expiry
    BEFORE INSERT ON otp_verifications
    FOR EACH ROW EXECUTE FUNCTION set_otp_expiry();

-- ============================================
-- PAYMENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN ('momo', 'vnpay', 'zalopay', 'bank_transfer')),
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending → completed → failed
    transaction_id VARCHAR(255),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);

-- ============================================
-- CHAT HISTORY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS chat_history (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(50) NOT NULL, -- Track conversation sessions
    user_id VARCHAR(50) NOT NULL, -- Track user for personalization
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    intent VARCHAR(100), -- recommend, book, status_check...
    entities JSONB, -- {"destination": "Đà Lạt", "people": 2}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_conversation ON chat_history(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_gin ON chat_history USING GIN(entities);

-- ============================================
-- FUNCTION: Search Tour Packages
-- ============================================
CREATE OR REPLACE FUNCTION search_tour_packages(
    search_destination VARCHAR DEFAULT '',
    min_budget DECIMAL DEFAULT 0,
    max_budget DECIMAL DEFAULT 999999999,
    start_after_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    package_id UUID, package_name VARCHAR, destination VARCHAR, 
    price DECIMAL, duration_days INTEGER, available_slots INTEGER,
    start_date DATE, image_urls TEXT, cuisine TEXT, suitable_for TEXT
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

-- ============================================
-- FUNCTION: Create Tour Booking
-- ============================================
CREATE OR REPLACE FUNCTION create_tour_booking(
    contact_name VARCHAR, contact_phone VARCHAR,
    package_id_param UUID, num_people INTEGER, special_requests TEXT DEFAULT NULL
)
RETURNS TABLE (booking_id UUID, total_amount DECIMAL, otp_code VARCHAR) AS $$
DECLARE
    pkg_price DECIMAL;
    new_booking_id UUID;
    otp_generated VARCHAR(6);
    calc_amount DECIMAL;
BEGIN
    -- Check package availability
    SELECT price INTO pkg_price FROM tour_packages 
    WHERE tour_packages.package_id = package_id_param 
        AND is_active = TRUE 
        AND available_slots >= num_people;
    IF NOT FOUND THEN 
        RAISE EXCEPTION 'Package not available'; 
    END IF;
    
    calc_amount := pkg_price * num_people;
    
    -- Create booking
    INSERT INTO bookings (package_id, number_of_people, total_amount, contact_name, contact_phone, special_requests, status)
    VALUES (package_id_param, num_people, calc_amount, contact_name, contact_phone, special_requests, 'otp_sent')
    RETURNING bookings.booking_id INTO new_booking_id;
    
    -- Generate OTP (6-digit code)
    otp_generated := LPAD((RANDOM() * 999999)::INTEGER::TEXT, 6, '0');
    
    -- Create OTP record
    INSERT INTO otp_verifications (booking_id, otp_code, phone_number) 
    VALUES (new_booking_id, otp_generated, contact_phone);
    
    -- Update available slots
    UPDATE tour_packages SET available_slots = available_slots - num_people WHERE tour_packages.package_id = package_id_param;
    
    RETURN QUERY SELECT new_booking_id, calc_amount, otp_generated;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- FUNCTION: Verify and Confirm Booking
-- ============================================
CREATE OR REPLACE FUNCTION verify_and_confirm_booking(booking_id_param UUID, otp_input VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    otp_rec RECORD;
BEGIN
    SELECT * INTO otp_rec FROM otp_verifications 
    WHERE booking_id = booking_id_param 
        AND otp_code = otp_input 
        AND expires_at > CURRENT_TIMESTAMP 
        AND is_verified = FALSE 
        AND attempts < 3;
    
    IF NOT FOUND THEN
        UPDATE otp_verifications SET attempts = attempts + 1 WHERE booking_id = booking_id_param;
        RETURN FALSE;
    END IF;
    
    UPDATE otp_verifications SET is_verified = TRUE, verified_at = CURRENT_TIMESTAMP WHERE booking_id = booking_id_param;
    UPDATE bookings SET status = 'confirmed' WHERE bookings.booking_id = booking_id_param;
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION: Check Schema
-- ============================================
-- ============================================
-- EMBEDDING SEARCH FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION match_packages(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    package_id UUID,
    package_name VARCHAR,
    destination VARCHAR,
    price DECIMAL,
    duration_days INTEGER,
    similarity FLOAT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tp.package_id,
        tp.package_name,
        tp.destination,
        tp.price,
        tp.duration_days,
        1 - (pe.embedding <=> query_embedding) AS similarity
    FROM package_embeddings pe
    JOIN tour_packages tp ON pe.package_id = tp.package_id
    WHERE tp.is_active = TRUE
    AND 1 - (pe.embedding <=> query_embedding) > match_threshold
    ORDER BY pe.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    RAISE NOTICE 'Schema initialization completed successfully!';
    RAISE NOTICE 'Created tables: tour_packages, bookings, package_embeddings, otp_verifications, payments, chat_history';
    RAISE NOTICE 'Created functions: search_tour_packages, create_tour_booking, verify_and_confirm_booking, match_packages';
    RAISE NOTICE 'Note: No users table - simplified for single user application';
END $$;

