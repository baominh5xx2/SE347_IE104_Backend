-- Migration: Add is_active column to users table
-- Description: Adds is_active boolean field for soft-disable functionality

-- Add is_active column with default true
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- Create index for filtering active users
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default  
FROM information_schema.columns
WHERE table_name = 'users' 
    AND column_name = 'is_active';
