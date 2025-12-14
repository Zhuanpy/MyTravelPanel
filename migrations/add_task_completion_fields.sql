-- ============================================
-- 任务完成记录字段 - 数据库迁移SQL
-- 适用于 MySQL Workbench
-- 执行前请备份数据库！
-- ============================================

-- 添加任务完成记录字段
ALTER TABLE todos 
ADD COLUMN completed_by INT NULL COMMENT '完成者用户ID',
ADD COLUMN completed_at DATETIME NULL COMMENT '完成时间';

-- 添加外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_completed_by 
FOREIGN KEY (completed_by) REFERENCES auth_users(id) 
ON DELETE SET NULL ON UPDATE CASCADE;

-- 添加索引
CREATE INDEX idx_todos_completed_by ON todos(completed_by);

-- ============================================
-- 验证：查看表结构
-- ============================================
-- DESCRIBE todos;

