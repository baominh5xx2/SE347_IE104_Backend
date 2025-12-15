-- Migration: Add last_access_time column to users table
-- Description: Tracks when user last accessed the system

-- Add last_access_time column (nullable, can be NULL for existing users)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_access_time TIMESTAMP;

-- Create index for sorting/filtering by last access time
CREATE INDEX IF NOT EXISTS idx_users_last_access_time ON users(last_access_time DESC);

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default  
FROM information_schema.columns
WHERE table_name = 'users' 
    AND column_name = 'last_access_time';
