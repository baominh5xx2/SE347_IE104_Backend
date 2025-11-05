-- ============================================
-- UPDATE CHAT HISTORY SCHEMA
-- Add conversation_id and user_id columns
-- ============================================

-- Add new columns to existing chat_history table
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS user_id VARCHAR(50);

-- Update existing records with default values
UPDATE chat_history 
SET 
    conversation_id = 'legacy_conv_' || message_id::text,
    user_id = 'legacy_user'
WHERE conversation_id IS NULL OR user_id IS NULL;

-- Make columns NOT NULL after updating existing data
ALTER TABLE chat_history 
ALTER COLUMN conversation_id SET NOT NULL,
ALTER COLUMN user_id SET NOT NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_conversation ON chat_history(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);

-- Add composite index for conversation queries
CREATE INDEX IF NOT EXISTS idx_chat_conv_created ON chat_history(conversation_id, created_at DESC);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check schema
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'chat_history' 
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'chat_history';

-- Sample data check
SELECT conversation_id, user_id, role, content, created_at 
FROM chat_history 
ORDER BY created_at DESC 
LIMIT 5;
