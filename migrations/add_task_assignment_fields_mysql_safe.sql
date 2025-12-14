-- ============================================
-- 任务中心功能 - 数据库迁移SQL（安全版本）
-- 适用于 MySQL Workbench
-- 此版本会先检查字段是否存在，避免重复添加
-- 执行前请备份数据库！
-- ============================================

-- 设置变量
SET @db_name = DATABASE();

-- ============================================
-- 步骤1: 安全添加字段（检查是否存在）
-- ============================================

-- 添加 assigned_to 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'assigned_to'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN assigned_to INT NULL COMMENT ''分配给的用户ID''',
    'SELECT ''字段 assigned_to 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 assigned_by 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'assigned_by'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN assigned_by INT NULL COMMENT ''分配者用户ID''',
    'SELECT ''字段 assigned_by 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 assigned_at 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'assigned_at'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN assigned_at DATETIME NULL COMMENT ''分配时间''',
    'SELECT ''字段 assigned_at 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 source_type 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'source_type'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN source_type VARCHAR(50) NULL COMMENT ''来源类型: visa, project, manual''',
    'SELECT ''字段 source_type 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 source_id 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'source_id'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN source_id INT NULL COMMENT ''来源业务数据ID''',
    'SELECT ''字段 source_id 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 reminder_days_before 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'reminder_days_before'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN reminder_days_before INT DEFAULT 0 COMMENT ''提前提醒天数''',
    'SELECT ''字段 reminder_days_before 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 auto_generated 字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND COLUMN_NAME = 'auto_generated'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE todos ADD COLUMN auto_generated TINYINT(1) DEFAULT 0 COMMENT ''是否自动生成''',
    'SELECT ''字段 auto_generated 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 步骤2: 添加外键约束（可选）
-- ============================================

-- 检查并添加 assigned_to 外键约束
SET @fk_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND CONSTRAINT_NAME = 'fk_todos_assigned_to'
);

SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE todos ADD CONSTRAINT fk_todos_assigned_to FOREIGN KEY (assigned_to) REFERENCES auth_users(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT ''外键 fk_todos_assigned_to 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 assigned_by 外键约束
SET @fk_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND CONSTRAINT_NAME = 'fk_todos_assigned_by'
);

SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE todos ADD CONSTRAINT fk_todos_assigned_by FOREIGN KEY (assigned_by) REFERENCES auth_users(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT ''外键 fk_todos_assigned_by 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 步骤3: 添加索引（检查是否存在）
-- ============================================

-- 检查并添加 assigned_to 索引
SET @idx_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND INDEX_NAME = 'idx_todos_assigned_to'
);

SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_todos_assigned_to ON todos(assigned_to)',
    'SELECT ''索引 idx_todos_assigned_to 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 source 联合索引
SET @idx_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND INDEX_NAME = 'idx_todos_source'
);

SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_todos_source ON todos(source_type, source_id)',
    'SELECT ''索引 idx_todos_source 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 user_id 索引（如果还没有）
SET @idx_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = @db_name 
      AND TABLE_NAME = 'todos' 
      AND INDEX_NAME = 'idx_todos_user_id'
);

SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_todos_user_id ON todos(user_id)',
    'SELECT ''索引 idx_todos_user_id 已存在，跳过'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 验证：查看表结构
-- ============================================
SELECT '迁移完成！请执行以下查询验证：' AS message;
SELECT 'DESCRIBE todos;' AS verification_query;

