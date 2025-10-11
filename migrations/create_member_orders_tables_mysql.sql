-- 创建会员订单相关表 (MySQL 版本)
-- 执行时间: 2025-01-XX
-- 说明: 创建会员订单系统的所有相关表，使用 member_ 前缀与 staff 订单系统区分
-- 数据库: MySQL/MariaDB

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. 创建会员订单主表
-- ============================================
DROP TABLE IF EXISTS `member_orders`;
CREATE TABLE `member_orders` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '订单ID',
    `order_number` VARCHAR(50) NOT NULL COMMENT '订单号',
    `user_id` INT(11) NOT NULL COMMENT '用户ID',
    
    -- 订单基本信息
    `service_type` VARCHAR(20) NOT NULL COMMENT '服务类型：visa, flight, hotel, tour, insurance, transfer',
    `service_name` VARCHAR(200) NOT NULL COMMENT '服务名称',
    `description` TEXT COMMENT '服务描述',
    
    -- 订单状态
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '订单状态：draft, pending, confirmed, in_progress, completed, cancelled, refunded',
    `priority` VARCHAR(20) DEFAULT 'normal' COMMENT '优先级：low, normal, high, urgent',
    
    -- 价格信息
    `base_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '基础价格',
    `additional_fees` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '附加费用',
    `discount_amount` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '折扣金额',
    `total_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '总金额',
    `currency` VARCHAR(3) DEFAULT 'SGD' COMMENT '货币单位',
    
    -- 时间信息
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `confirmed_at` DATETIME DEFAULT NULL COMMENT '确认时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    `cancelled_at` DATETIME DEFAULT NULL COMMENT '取消时间',
    
    -- 客户信息
    `customer_name` VARCHAR(100) NOT NULL COMMENT '客户姓名',
    `customer_email` VARCHAR(120) NOT NULL COMMENT '客户邮箱',
    `customer_phone` VARCHAR(20) DEFAULT NULL COMMENT '客户电话',
    `customer_address` TEXT COMMENT '客户地址',
    
    -- 特殊要求
    `special_requirements` TEXT COMMENT '特殊要求',
    `notes` TEXT COMMENT '备注',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_order_number` (`order_number`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_status` (`status`),
    KEY `idx_service_type` (`service_type`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_member_orders_user` FOREIGN KEY (`user_id`) REFERENCES `auth_users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员订单主表';

-- ============================================
-- 2. 创建会员订单项目表
-- ============================================
DROP TABLE IF EXISTS `member_order_items`;
CREATE TABLE `member_order_items` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '项目ID',
    `order_id` INT(11) NOT NULL COMMENT '订单ID',
    
    -- 项目信息
    `item_name` VARCHAR(200) NOT NULL COMMENT '项目名称',
    `item_description` TEXT COMMENT '项目描述',
    `item_type` VARCHAR(50) DEFAULT NULL COMMENT '项目类型',
    
    -- 数量和价格
    `quantity` INT(11) DEFAULT 1 COMMENT '数量',
    `unit_price` DECIMAL(10, 2) NOT NULL COMMENT '单价',
    `total_price` DECIMAL(10, 2) NOT NULL COMMENT '总价',
    
    -- 特殊属性
    `properties` JSON DEFAULT NULL COMMENT '特殊属性（JSON格式）',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_order_id` (`order_id`),
    CONSTRAINT `fk_member_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `member_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员订单项目表';

-- ============================================
-- 3. 创建会员订单文档表
-- ============================================
DROP TABLE IF EXISTS `member_order_documents`;
CREATE TABLE `member_order_documents` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '文档ID',
    `order_id` INT(11) NOT NULL COMMENT '订单ID',
    
    -- 文档信息
    `document_name` VARCHAR(200) NOT NULL COMMENT '文档名称',
    `document_type` VARCHAR(50) NOT NULL COMMENT '文档类型：passport, photo, form, etc.',
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
    `file_size` INT(11) DEFAULT NULL COMMENT '文件大小（字节）',
    `mime_type` VARCHAR(100) DEFAULT NULL COMMENT 'MIME类型',
    
    -- 状态
    `is_verified` TINYINT(1) DEFAULT 0 COMMENT '是否已验证：0-未验证, 1-已验证',
    `verification_notes` TEXT COMMENT '验证备注',
    
    `uploaded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    `verified_at` DATETIME DEFAULT NULL COMMENT '验证时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_order_id` (`order_id`),
    KEY `idx_document_type` (`document_type`),
    CONSTRAINT `fk_member_order_documents_order` FOREIGN KEY (`order_id`) REFERENCES `member_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员订单文档表';

-- ============================================
-- 4. 创建会员订单支付表
-- ============================================
DROP TABLE IF EXISTS `member_order_payments`;
CREATE TABLE `member_order_payments` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '支付ID',
    `order_id` INT(11) NOT NULL COMMENT '订单ID',
    
    -- 支付信息
    `payment_method` VARCHAR(50) NOT NULL COMMENT '支付方式：credit_card, bank_transfer, paypal, etc.',
    `payment_reference` VARCHAR(100) DEFAULT NULL COMMENT '支付参考号',
    `amount` DECIMAL(10, 2) NOT NULL COMMENT '支付金额',
    `currency` VARCHAR(3) DEFAULT 'SGD' COMMENT '货币单位',
    
    -- 状态
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '支付状态：pending, completed, failed, refunded',
    `transaction_id` VARCHAR(100) DEFAULT NULL COMMENT '交易ID',
    
    -- 时间
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_order_id` (`order_id`),
    KEY `idx_status` (`status`),
    KEY `idx_payment_reference` (`payment_reference`),
    CONSTRAINT `fk_member_order_payments_order` FOREIGN KEY (`order_id`) REFERENCES `member_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员订单支付表';

-- ============================================
-- 5. 创建会员服务模板表
-- ============================================
DROP TABLE IF EXISTS `member_service_templates`;
CREATE TABLE `member_service_templates` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '模板ID',
    
    -- 服务基本信息
    `service_type` VARCHAR(20) NOT NULL COMMENT '服务类型：visa, flight, hotel, tour, insurance, transfer',
    `service_name` VARCHAR(200) NOT NULL COMMENT '服务名称',
    `description` TEXT COMMENT '服务描述',
    
    -- 价格信息
    `base_price` DECIMAL(10, 2) NOT NULL COMMENT '基础价格',
    `currency` VARCHAR(3) DEFAULT 'SGD' COMMENT '货币单位',
    
    -- 处理信息
    `processing_time` VARCHAR(100) DEFAULT NULL COMMENT '处理时间描述',
    `requirements` TEXT COMMENT '服务要求描述',
    `required_documents` JSON DEFAULT NULL COMMENT '必需文档列表（JSON格式）',
    
    -- 状态
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活：0-停用, 1-启用',
    `is_featured` TINYINT(1) DEFAULT 0 COMMENT '是否推荐：0-否, 1-是',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_service_type` (`service_type`),
    KEY `idx_is_active` (`is_active`),
    KEY `idx_is_featured` (`is_featured`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员服务模板表';

-- ============================================
-- 插入示例服务模板数据
-- ============================================
INSERT INTO `member_service_templates` 
    (`service_type`, `service_name`, `description`, `base_price`, `currency`, `processing_time`, `requirements`, `required_documents`, `is_active`, `is_featured`)
VALUES 
    ('visa', '新加坡旅游签证', '为中国公民提供新加坡旅游签证办理服务', 50.00, 'SGD', '3-5个工作日', 
     '护照有效期至少6个月，提供完整材料', 
     JSON_ARRAY('护照原件', '2张2寸白底彩色照片', '签证申请表', '往返机票预订单', '酒店预订单'), 
     1, 1),
    
    ('visa', '泰国旅游签证', '为中国公民提供泰国旅游签证办理服务', 40.00, 'SGD', '2-3个工作日', 
     '护照有效期至少6个月，提供完整材料', 
     JSON_ARRAY('护照原件', '2张2寸白底彩色照片', '签证申请表', '往返机票预订单'), 
     1, 0),
    
    ('visa', '马来西亚旅游签证', '为中国公民提供马来西亚旅游签证办理服务', 35.00, 'SGD', '2-3个工作日', 
     '护照有效期至少6个月，提供完整材料', 
     JSON_ARRAY('护照原件', '2张2寸白底彩色照片', '签证申请表'), 
     1, 0),
    
    ('flight', '国际机票预订', '提供全球航线机票预订服务', 0.00, 'SGD', '即时出票', 
     '提供准确的乘客信息和航班需求', 
     JSON_ARRAY('护照信息', '联系方式'), 
     1, 0),
    
    ('hotel', '酒店预订服务', '提供全球酒店预订服务', 0.00, 'SGD', '即时确认', 
     '提供入住日期和要求', 
     JSON_ARRAY('入住人信息', '特殊要求'), 
     1, 0),
    
    ('tour', '东南亚旅游套餐', '精心设计的东南亚旅游线路', 999.00, 'SGD', '提前3天预订', 
     '至少提前3天预订，提供完整的旅客信息', 
     JSON_ARRAY('护照信息', '紧急联系人', '特殊需求说明'), 
     1, 1),
    
    ('tour', '新马泰经典7日游', '新加坡-马来西亚-泰国经典线路', 1299.00, 'SGD', '提前5天预订', 
     '至少提前5天预订，包含机票、酒店和导游服务', 
     JSON_ARRAY('护照信息', '紧急联系人', '健康声明'), 
     1, 1);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 验证表创建
-- ============================================
SELECT 
    'Member orders tables created successfully!' AS status,
    (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'member_%') AS tables_created,
    (SELECT COUNT(*) FROM member_service_templates) AS template_count;
