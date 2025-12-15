-- Migration: Add user_id to bookings and payments tables
-- Description: Links bookings and payments directly to users for admin management

-- ============================================
-- ADD user_id TO BOOKINGS TABLE
-- ============================================
ALTER TABLE bookings
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(user_id) ON DELETE CASCADE;

-- Create index for user_id queries
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);

-- Create composite index for user + status queries
CREATE INDEX IF NOT EXISTS idx_bookings_user_status ON bookings(user_id, status);

-- ============================================
-- ADD user_id TO PAYMENTS TABLE
-- ============================================
ALTER TABLE payments
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(user_id) ON DELETE CASCADE;

-- Create index for user_id queries
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);

-- Create composite index for user + payment_status queries
CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, payment_status);

-- ============================================
-- VERIFY MIGRATION
-- ============================================
SELECT 
    table_name,
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('bookings', 'payments') 
    AND column_name = 'user_id'
ORDER BY table_name;
