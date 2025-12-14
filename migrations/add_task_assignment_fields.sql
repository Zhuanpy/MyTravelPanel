-- 添加任务分配相关字段到todos表
-- 执行前请备份数据库

-- 添加任务分配字段
ALTER TABLE todos 
ADD COLUMN assigned_to INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_by INTEGER REFERENCES auth_users(id),
ADD COLUMN assigned_at DATETIME,
ADD COLUMN source_type VARCHAR(50),
ADD COLUMN source_id INTEGER,
ADD COLUMN reminder_days_before INTEGER DEFAULT 0,
ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;

-- 添加索引提高查询性能
CREATE INDEX IF NOT EXISTS idx_todos_assigned_to ON todos(assigned_to);
CREATE INDEX IF NOT EXISTS idx_todos_source ON todos(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id);

-- 如果索引已存在，上面的CREATE INDEX IF NOT EXISTS可能不支持，可以使用以下方式：
-- CREATE INDEX idx_todos_assigned_to ON todos(assigned_to);
-- CREATE INDEX idx_todos_source ON todos(source_type, source_id);
-- CREATE INDEX idx_todos_user_id ON todos(user_id);

