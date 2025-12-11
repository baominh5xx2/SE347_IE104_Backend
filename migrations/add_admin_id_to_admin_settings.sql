-- =====================================================
-- Migration: Add admin_id column to admin_settings
-- Description: Track which admin updated the setting
-- Date: 2025-01-XX
-- =====================================================

-- Add admin_id column
ALTER TABLE admin_settings
ADD COLUMN IF NOT EXISTS admin_id VARCHAR;

-- Add comment
COMMENT ON COLUMN admin_settings.admin_id IS 'Admin user ID who last updated this setting';

-- Optional: backfill admin_id from updated_by if present
-- UPDATE admin_settings SET admin_id = updated_by WHERE admin_id IS NULL AND updated_by IS NOT NULL;

-- Update statistics
ANALYZE admin_settings;


