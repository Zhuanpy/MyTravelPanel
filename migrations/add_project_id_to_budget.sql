-- 添加 project_id 字段到 package_budget_header 表
-- 用于关联预算和旅游项目

-- 检查字段是否存在，不存在则添加
SET @dbname = DATABASE();
SET @tablename = 'package_budget_header';
SET @columnname = 'project_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加索引（如果不存在）
SET @indexname = 'idx_budget_project_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND INDEX_NAME = @indexname
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (project_id)')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- 添加外键约束（可选，如果需要严格约束）
-- ALTER TABLE package_budget_header 
-- ADD CONSTRAINT fk_budget_project 
-- FOREIGN KEY (project_id) REFERENCES tour_projects(id) ON DELETE SET NULL;

SELECT 'Migration completed: project_id field added to package_budget_header' AS result;
