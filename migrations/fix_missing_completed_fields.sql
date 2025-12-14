-- ============================================
-- 修复缺失字段：添加任务完成记录字段
-- 适用于 MySQL Workbench
-- 解决错误：Unknown column 'todos.completed_by' in 'field list'
-- ============================================
-- 执行前请备份数据库！

-- 检查并添加 completed_by 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'completed_by'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN completed_by INT NULL COMMENT ''完成者用户ID''',
    'SELECT ''字段 completed_by 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 completed_at 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'completed_at'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN completed_at DATETIME NULL COMMENT ''完成时间''',
    'SELECT ''字段 completed_at 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加外键约束
SET @fk_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'todos' 
      AND CONSTRAINT_NAME = 'fk_todos_completed_by'
);

SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE todos ADD CONSTRAINT fk_todos_completed_by FOREIGN KEY (completed_by) REFERENCES auth_users(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT ''外键 fk_todos_completed_by 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加索引
SET @idx_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'todos' 
      AND INDEX_NAME = 'idx_todos_completed_by'
);

SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_todos_completed_by ON todos(completed_by)',
    'SELECT ''索引 idx_todos_completed_by 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 验证：查看表结构
-- ============================================
SELECT '迁移完成！请执行以下查询验证：' AS message;
SELECT 'DESCRIBE todos;' AS verification_query;

