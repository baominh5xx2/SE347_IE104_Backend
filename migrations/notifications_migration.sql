-- Migration: Create notifications table
-- Description: Store user notifications for tour cancellations, bookings, etc
-- Created: 2025-12-17
-- =============================================

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,  -- 'tour_cancelled', 'booking_cancelled', 'booking_confirmed', 'payment_success'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,  -- {package_id, booking_id, package_name, etc}
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
    ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read 
    ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
    ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
    ON notifications(user_id, is_read) 
    WHERE is_read = FALSE;

-- Add comment
COMMENT ON TABLE notifications IS 
'Stores user notifications for various events like tour cancellations, booking confirmations, etc.';

-- Grant access
GRANT ALL ON notifications TO authenticated;

-- =============================================
-- Verification
-- =============================================
-- SELECT * FROM notifications LIMIT 10;
