-- ============================================
-- 任务中心功能 - 完整数据库迁移SQL
-- 适用于 MySQL Workbench
-- 包含：任务分配字段 + 任务完成记录字段
-- 执行前请备份数据库！
-- ============================================

-- ============================================
-- 第一部分：任务分配字段
-- ============================================

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
-- 第二部分：任务完成记录字段
-- ============================================

-- 添加 completed_by 字段（完成者用户ID）
ALTER TABLE todos 
ADD COLUMN completed_by INT NULL COMMENT '完成者用户ID';

-- 添加 completed_at 字段（完成时间）
ALTER TABLE todos 
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间';

-- ============================================
-- 第三部分：外键约束
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

-- 添加 completed_by 外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_completed_by 
FOREIGN KEY (completed_by) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- ============================================
-- 第四部分：索引
-- ============================================

-- 为 assigned_to 添加索引
CREATE INDEX idx_todos_assigned_to ON todos(assigned_to);

-- 为 source_type 和 source_id 添加联合索引
CREATE INDEX idx_todos_source ON todos(source_type, source_id);

-- 为 user_id 添加索引（如果还没有）
CREATE INDEX idx_todos_user_id ON todos(user_id);

-- 为 completed_by 添加索引
CREATE INDEX idx_todos_completed_by ON todos(completed_by);

-- ============================================
-- 验证：查看表结构
-- ============================================
-- DESCRIBE todos;

-- ============================================
-- 检查字段是否已添加（可选执行）
-- ============================================
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
--   AND TABLE_NAME = 'todos' 
--   AND COLUMN_NAME IN (
--       'assigned_to', 'assigned_by', 'assigned_at', 
--       'source_type', 'source_id', 'reminder_days_before', 'auto_generated',
--       'completed_by', 'completed_at'
--   )
-- ORDER BY COLUMN_NAME;
