-- ============================================
-- Add Role Column to Users Table
-- Migration để thêm phân quyền admin/user
-- ============================================

-- Thêm column role vào users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';

-- Thêm constraint để chỉ cho phép 'user' hoặc 'admin'
DO $$
BEGIN
    -- Drop constraint nếu đã tồn tại
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_role_check'
    ) THEN
        ALTER TABLE users DROP CONSTRAINT users_role_check;
    END IF;
    
    -- Thêm constraint mới
    ALTER TABLE users 
    ADD CONSTRAINT users_role_check CHECK (role IN ('user', 'admin'));
END $$;

-- Update existing users: set role = 'user' nếu NULL
UPDATE users 
SET role = 'user' 
WHERE role IS NULL;

-- Tạo index để optimize queries theo role
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Verification query
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
    AND column_name = 'role'; -- Đã sửa: Thêm điều kiện so sánh = 'role'

-- Check constraint
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'users'::regclass
    AND conname = 'users_role_check';