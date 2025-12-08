-- ============================================
-- CHAT ROOM MANAGEMENT SYSTEM
-- Migration script to create chat_rooms table and improve chat_history
-- ============================================

-- Create chat_rooms table
CREATE TABLE IF NOT EXISTS chat_rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for chat_rooms
CREATE INDEX IF NOT EXISTS idx_chat_rooms_user ON chat_rooms(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_rooms_archived ON chat_rooms(user_id, is_archived, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_rooms_updated ON chat_rooms(updated_at DESC);

-- Add room_id and message_order to chat_history table
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS room_id UUID REFERENCES chat_rooms(room_id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS message_order INTEGER DEFAULT 0;

-- Update existing chat_history records
-- Create rooms from existing conversation_id and link messages
-- Note: Skip records where user_id is not a valid UUID (legacy data)
DO $$
DECLARE
    conv_record RECORD;
    new_room_id UUID;
    msg_count INTEGER;
    valid_user_id UUID;
BEGIN
    -- Loop through unique conversation_id values using GROUP BY
    -- Only process records where user_id can be converted to UUID
    FOR conv_record IN 
        SELECT 
            conversation_id, 
            user_id,
            MIN(created_at) as min_created_at
        FROM chat_history 
        WHERE room_id IS NULL
        GROUP BY conversation_id, user_id
        ORDER BY min_created_at
    LOOP
        -- Try to convert user_id to UUID
        -- If conversion fails, skip this record (legacy data)
        BEGIN
            -- Check if user_id matches UUID format (8-4-4-4-12 hex digits)
            IF conv_record.user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                valid_user_id := conv_record.user_id::UUID;
            ELSE
                -- Skip legacy user_id formats (like "user_491f5ad718c0")
                RAISE NOTICE 'Skipping conversation % with non-UUID user_id: %', conv_record.conversation_id, conv_record.user_id;
                CONTINUE;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- Skip if conversion fails
            RAISE NOTICE 'Skipping conversation % due to invalid user_id: %', conv_record.conversation_id, conv_record.user_id;
            CONTINUE;
        END;
        
        -- Create a new room for this conversation
        INSERT INTO chat_rooms (user_id, title, created_at, updated_at)
        VALUES (
            valid_user_id,
            'Cuộc trò chuyện cũ',
            (SELECT MIN(created_at) FROM chat_history WHERE conversation_id = conv_record.conversation_id),
            (SELECT MAX(created_at) FROM chat_history WHERE conversation_id = conv_record.conversation_id)
        )
        RETURNING room_id INTO new_room_id;
        
        -- Update messages with room_id and message_order
        WITH ordered_messages AS (
            SELECT message_id, ROW_NUMBER() OVER (ORDER BY created_at) as msg_order
            FROM chat_history
            WHERE conversation_id = conv_record.conversation_id
        )
        UPDATE chat_history ch
        SET room_id = new_room_id,
            message_order = om.msg_order
        FROM ordered_messages om
        WHERE ch.message_id = om.message_id;
        
        -- Update room title from first user message
        UPDATE chat_rooms
        SET title = LEFT(
            (SELECT content FROM chat_history 
             WHERE room_id = new_room_id 
             AND role = 'user' 
             ORDER BY created_at ASC 
             LIMIT 1),
            50
        )
        WHERE room_id = new_room_id;
    END LOOP;
END $$;

-- Make room_id NOT NULL after migration (if all records have room_id)
-- Note: This might fail if there are still NULL values, so we'll keep it nullable for now
-- ALTER TABLE chat_history ALTER COLUMN room_id SET NOT NULL;

-- Create indexes for chat_history with room_id
CREATE INDEX IF NOT EXISTS idx_chat_history_room ON chat_history(room_id, message_order ASC);
CREATE INDEX IF NOT EXISTS idx_chat_history_room_created ON chat_history(room_id, created_at DESC);

-- Function to update room updated_at when message is added
CREATE OR REPLACE FUNCTION update_chat_room_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_rooms
    SET updated_at = CURRENT_TIMESTAMP
    WHERE room_id = NEW.room_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update room timestamp
DROP TRIGGER IF EXISTS trigger_update_chat_room_timestamp ON chat_history;
CREATE TRIGGER trigger_update_chat_room_timestamp
    AFTER INSERT ON chat_history
    FOR EACH ROW
    WHEN (NEW.room_id IS NOT NULL)
    EXECUTE FUNCTION update_chat_room_timestamp();

-- Function to get message count for a room
CREATE OR REPLACE FUNCTION get_room_message_count(room_uuid UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM chat_history WHERE room_id = room_uuid);
END;
$$ LANGUAGE plpgsql;

-- Function to get message counts for multiple rooms (tối ưu N+1 query)
CREATE OR REPLACE FUNCTION get_room_message_counts(room_ids UUID[])
RETURNS TABLE(room_id UUID, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ch.room_id,
        COUNT(*)::BIGINT as count
    FROM chat_history ch
    WHERE ch.room_id = ANY(room_ids)
    GROUP BY ch.room_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get last message for a room
CREATE OR REPLACE FUNCTION get_room_last_message(room_uuid UUID)
RETURNS TEXT AS $$
BEGIN
    RETURN (
        SELECT content 
        FROM chat_history 
        WHERE room_id = room_uuid 
        ORDER BY created_at DESC 
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get last message timestamp for a room
CREATE OR REPLACE FUNCTION get_room_last_message_at(room_uuid UUID)
RETURNS TIMESTAMP AS $$
BEGIN
    RETURN (
        SELECT created_at 
        FROM chat_history 
        WHERE room_id = room_uuid 
        ORDER BY created_at DESC 
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

