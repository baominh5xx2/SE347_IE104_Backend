-- Add 'admin' to the allowed roles in chat_history
ALTER TABLE chat_history DROP CONSTRAINT IF EXISTS chat_history_role_check;

ALTER TABLE chat_history 
ADD CONSTRAINT chat_history_role_check 
CHECK (role IN ('user', 'assistant', 'system', 'admin'));
