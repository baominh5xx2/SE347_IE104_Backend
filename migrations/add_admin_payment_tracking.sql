-- Migration: Add admin payment tracking and refund support
-- Description: Track manual payments created by admin and refund information
-- Date: 2025-12-17

-- Add admin tracking columns for manual payments
ALTER TABLE payments
ADD COLUMN IF NOT EXISTS created_by_admin_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS refunded_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS refund_amount DECIMAL(12, 2),
ADD COLUMN IF NOT EXISTS refund_reason TEXT;

-- Add comments
COMMENT ON COLUMN payments.created_by_admin_id IS 'Admin user ID who manually created this payment (NULL for user-created payments)';
COMMENT ON COLUMN payments.refunded_by IS 'Admin user ID who processed the refund';
COMMENT ON COLUMN payments.refunded_at IS 'Timestamp when refund was processed';
COMMENT ON COLUMN payments.refund_amount IS 'Amount refunded to user';
COMMENT ON COLUMN payments.refund_reason IS 'Admin reason for refund';

-- Create index for refund queries
CREATE INDEX IF NOT EXISTS idx_payments_refunded 
    ON payments(refunded_at) 
    WHERE refunded_at IS NOT NULL;

-- Create index for admin-created payments
CREATE INDEX IF NOT EXISTS idx_payments_admin_created 
    ON payments(created_by_admin_id) 
    WHERE created_by_admin_id IS NOT NULL;

-- Update statistics
ANALYZE payments;
