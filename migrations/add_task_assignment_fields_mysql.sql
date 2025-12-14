-- ============================================
-- 任务中心功能 - 数据库迁移SQL
-- 适用于 MySQL Workbench
-- 执行前请备份数据库！
-- ============================================

-- 步骤1: 检查并添加新字段
-- 如果字段已存在会报错，可以忽略或先检查

-- 添加 assigned_to 字段（分配给的用户ID）
ALTER TABLE todos 
ADD COLUMN assigned_to INT NULL COMMENT '分配给的用户ID';

-- 添加 assigned_by 字段（分配者用户ID）
ALTER TABLE todos 
ADD COLUMN assigned_by INT NULL COMMENT '分配者用户ID';

-- 添加 assigned_at 字段（分配时间）
ALTER TABLE todos 
ADD COLUMN assigned_at DATETIME NULL COMMENT '分配时间';

-- 添加 source_type 字段（来源类型）
ALTER TABLE todos 
ADD COLUMN source_type VARCHAR(50) NULL COMMENT '来源类型: visa, project, manual';

-- 添加 source_id 字段（来源业务数据ID）
ALTER TABLE todos 
ADD COLUMN source_id INT NULL COMMENT '来源业务数据ID';

-- 添加 reminder_days_before 字段（提前提醒天数）
ALTER TABLE todos 
ADD COLUMN reminder_days_before INT DEFAULT 0 COMMENT '提前提醒天数';

-- 添加 auto_generated 字段（是否自动生成）
ALTER TABLE todos 
ADD COLUMN auto_generated TINYINT(1) DEFAULT 0 COMMENT '是否自动生成';

-- ============================================
-- 步骤2: 添加外键约束（可选，如果不需要外键约束可以跳过）
-- ============================================

-- 添加 assigned_to 外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_assigned_to 
FOREIGN KEY (assigned_to) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- 添加 assigned_by 外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_assigned_by 
FOREIGN KEY (assigned_by) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- ============================================
-- 步骤3: 添加索引提高查询性能
-- ============================================

-- 检查索引是否存在，如果不存在则创建
-- 注意：MySQL不支持 IF NOT EXISTS，如果索引已存在会报错，可以忽略

-- 为 assigned_to 添加索引
CREATE INDEX idx_todos_assigned_to ON todos(assigned_to);

-- 为 source_type 和 source_id 添加联合索引
CREATE INDEX idx_todos_source ON todos(source_type, source_id);

-- 为 user_id 添加索引（如果还没有的话
CREATE INDEX idx_todos_user_id ON todos(user_id);

-- ============================================
-- 验证：查询表结构确认字段已添加
-- ============================================
-- 执行以下查询可以查看 todos 表的结构
-- DESCRIBE todos;
-- 或
-- SHOW COLUMNS FROM todos;

-- ============================================
-- 如果执行出错，可以使用以下语句检查字段是否已存在
-- ============================================
-- SELECT COLUMN_NAME 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
--   AND TABLE_NAME = 'todos' 
--   AND COLUMN_NAME IN ('assigned_to', 'assigned_by', 'assigned_at', 'source_type', 'source_id', 'reminder_days_before', 'auto_generated');

