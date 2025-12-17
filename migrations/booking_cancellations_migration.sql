-- Migration: Create booking_cancellations table
-- Description: Store booking cancellation history (full booking snapshot)
-- Created: 2025-12-17
-- =============================================

-- Drop existing table if it has old structure
DROP TABLE IF EXISTS booking_cancellations;

-- Create booking_cancellations table (stores full booking snapshot)
CREATE TABLE IF NOT EXISTS booking_cancellations (
    cancellation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id),
    package_id UUID NOT NULL REFERENCES tour_packages(package_id),
    
    -- Booking snapshot fields
    number_of_people INT NOT NULL,
    total_amount NUMERIC(12, 2),
    contact_name VARCHAR(255),
    contact_phone VARCHAR(15),
    contact_email VARCHAR(255),
    special_requests TEXT,
    previous_status VARCHAR(50) NOT NULL, -- Status before cancellation (pending/confirmed)
    promotion_id UUID,
    booking_created_at TIMESTAMP WITH TIME ZONE,
    
    -- Cancellation info
    reason TEXT,
    cancelled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cancelled_by VARCHAR(20) NOT NULL DEFAULT 'user', -- 'user' | 'admin' | 'system'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_booking_cancellations_booking_id 
    ON booking_cancellations(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_cancellations_user_id 
    ON booking_cancellations(user_id);
CREATE INDEX IF NOT EXISTS idx_booking_cancellations_cancelled_at 
    ON booking_cancellations(cancelled_at);

-- Add comment
COMMENT ON TABLE booking_cancellations IS 
'Stores booking cancellation history. When a booking is cancelled, 
a record is inserted here and booking.status is set to cancelled (soft delete).';

-- Grant access
GRANT ALL ON booking_cancellations TO authenticated;

-- =============================================
-- Verification
-- =============================================
-- SELECT * FROM booking_cancellations LIMIT 5;
