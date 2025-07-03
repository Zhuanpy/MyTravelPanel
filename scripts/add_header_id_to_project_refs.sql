-- 为project_refs表添加header_id字段的SQL脚本

-- 检查字段是否存在，如果不存在则添加
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'project_refs' 
     AND COLUMN_NAME = 'header_id') = 0,
    'ALTER TABLE `project_refs` ADD COLUMN `header_id` int(11) NOT NULL COMMENT ''HID主表ID'' AFTER `id`',
    'SELECT ''header_id column already exists'' as message'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加外键约束（如果不存在）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'project_refs' 
     AND COLUMN_NAME = 'header_id' 
     AND CONSTRAINT_NAME = 'fk_project_refs_header') = 0,
    'ALTER TABLE `project_refs` ADD CONSTRAINT `fk_project_refs_header` FOREIGN KEY (`header_id`) REFERENCES `project_headers` (`id`) ON DELETE CASCADE',
    'SELECT ''foreign key constraint already exists'' as message'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加索引（如果不存在）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'project_refs' 
     AND INDEX_NAME = 'idx_header_id') = 0,
    'ALTER TABLE `project_refs` ADD INDEX `idx_header_id` (`header_id`)',
    'SELECT ''index already exists'' as message'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt; 