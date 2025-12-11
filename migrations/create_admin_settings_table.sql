-- =====================================================
-- Migration: Create Admin Settings Table
-- Description: Store admin configuration settings (e.g., ADMIN_RECOMMENDATION_ENABLED)
-- Date: 2025-01-XX
-- =====================================================

-- Create admin_settings table
CREATE TABLE IF NOT EXISTS admin_settings (
    setting_key VARCHAR(255) PRIMARY KEY,
    setting_value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) -- Optional: track who updated
);

-- Add comment
COMMENT ON TABLE admin_settings IS 'Stores admin configuration settings (key-value store)';
COMMENT ON COLUMN admin_settings.setting_key IS 'Unique setting key (e.g., ADMIN_RECOMMENDATION_ENABLED)';
COMMENT ON COLUMN admin_settings.setting_value IS 'Setting value as JSON (supports boolean, string, number, object)';
COMMENT ON COLUMN admin_settings.updated_at IS 'Last update timestamp';
COMMENT ON COLUMN admin_settings.updated_by IS 'User ID who made the update';

-- Create index on updated_at for querying recent changes
CREATE INDEX IF NOT EXISTS idx_admin_settings_updated_at ON admin_settings(updated_at);

-- Insert default value for ADMIN_RECOMMENDATION_ENABLED
INSERT INTO admin_settings (setting_key, setting_value, updated_at)
VALUES ('ADMIN_RECOMMENDATION_ENABLED', 'false'::jsonb, CURRENT_TIMESTAMP)
ON CONFLICT (setting_key) DO NOTHING;

-- Update statistics
ANALYZE admin_settings;

-- Verification query (run manually to check)
-- SELECT * FROM admin_settings WHERE setting_key = 'ADMIN_RECOMMENDATION_ENABLED';

