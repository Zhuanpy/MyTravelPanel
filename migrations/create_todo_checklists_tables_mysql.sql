-- =====================================================
-- 创建任务清单相关表 (MySQL 版本)
-- 用于支持重复任务和任务模板功能
-- =====================================================

-- 1. 创建任务清单表
CREATE TABLE IF NOT EXISTS `todo_checklists` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL COMMENT '清单名称',
    `description` TEXT COMMENT '清单描述',
    `category` VARCHAR(50) DEFAULT NULL COMMENT '分类',
    `is_recurring` TINYINT(1) DEFAULT 0 COMMENT '是否为重复任务',
    `recurrence_type` VARCHAR(20) DEFAULT NULL COMMENT '重复类型: daily, weekly, monthly',
    `recurrence_days` VARCHAR(50) DEFAULT NULL COMMENT '重复的星期几（用于weekly）：1,2,3,4,5,6,0（周一到周日）',
    `recurrence_time` VARCHAR(10) DEFAULT NULL COMMENT '重复的时间: HH:MM',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `user_id` INT DEFAULT NULL COMMENT '用户ID',
    `last_generated_at` DATETIME DEFAULT NULL COMMENT '最后一次生成任务的时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_is_recurring` (`is_recurring`),
    CONSTRAINT `fk_checklist_user` FOREIGN KEY (`user_id`) 
        REFERENCES `auth_users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务清单表';

-- 2. 创建任务清单项表
CREATE TABLE IF NOT EXISTS `todo_checklist_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `checklist_id` INT NOT NULL COMMENT '所属清单ID',
    `title` VARCHAR(255) NOT NULL COMMENT '任务标题',
    `description` TEXT COMMENT '任务描述',
    `priority` INT DEFAULT 2 COMMENT '优先级：1=高，2=中，3=低',
    `order_index` INT DEFAULT 0 COMMENT '排序索引',
    INDEX `idx_checklist_id` (`checklist_id`),
    INDEX `idx_order_index` (`order_index`),
    CONSTRAINT `fk_item_checklist` FOREIGN KEY (`checklist_id`) 
        REFERENCES `todo_checklists`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务清单项表';

-- 3. 验证表是否创建成功
SELECT 
    TABLE_NAME as '表名',
    TABLE_ROWS as '行数',
    CREATE_TIME as '创建时间'
FROM 
    information_schema.TABLES 
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME IN ('todo_checklists', 'todo_checklist_items');

-- 4. 查看表结构
SHOW CREATE TABLE todo_checklists;
SHOW CREATE TABLE todo_checklist_items;

-- =====================================================
-- 使用说明：
-- 
-- 在 MySQL Workbench 中执行：
-- 1. 打开此文件
-- 2. 选择正确的数据库（Schema）
-- 3. 点击执行（闪电图标）或按 Ctrl+Shift+Enter
--
-- 或在命令行执行：
-- mysql -u username -p database_name < migrations/create_todo_checklists_tables_mysql.sql
-- =====================================================











