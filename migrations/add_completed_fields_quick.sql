-- ============================================
-- 快速修复：添加任务完成记录字段
-- 适用于 MySQL Workbench
-- 解决错误：Unknown column 'todos.completed_by' in 'field list'
-- ============================================

-- 添加 completed_by 字段（完成者用户ID）
ALTER TABLE todos 
ADD COLUMN completed_by INT NULL COMMENT '完成者用户ID';

-- 添加 completed_at 字段（完成时间）
ALTER TABLE todos 
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间';

-- 添加外键约束（可选，如果不需要外键可以跳过）
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_completed_by 
FOREIGN KEY (completed_by) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- 添加索引（提高查询性能）
CREATE INDEX idx_todos_completed_by ON todos(completed_by);

-- ============================================
-- 验证：查看表结构
-- ============================================
-- DESCRIBE todos;

