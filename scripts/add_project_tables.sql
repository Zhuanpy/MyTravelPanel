-- 添加项目相关表的SQL脚本

-- 1. 创建客户公司表
CREATE TABLE IF NOT EXISTS `customer_companies` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `company_name` varchar(100) NOT NULL COMMENT '公司名称',
    `company_code` varchar(50) DEFAULT NULL COMMENT '公司代码',
    `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
    `contact_phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
    `contact_email` varchar(100) DEFAULT NULL COMMENT '联系邮箱',
    `address` text DEFAULT NULL COMMENT '公司地址',
    `industry` varchar(50) DEFAULT NULL COMMENT '行业',
    `company_size` varchar(20) DEFAULT NULL COMMENT '公司规模',
    `credit_limit` decimal(15,2) DEFAULT NULL COMMENT '信用额度',
    `currency` varchar(10) DEFAULT 'SGD' COMMENT '币种',
    `status` enum('active','inactive','suspended') DEFAULT 'active' COMMENT '状态',
    `remarks` text DEFAULT NULL COMMENT '备注',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户公司表';

-- 2. 创建客户表
CREATE TABLE IF NOT EXISTS `customers` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(100) NOT NULL COMMENT '客户名称',
    `phone` varchar(20) DEFAULT NULL COMMENT '电话',
    `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
    `id_number` varchar(30) DEFAULT NULL COMMENT '证件号码',
    `id_type` varchar(20) DEFAULT NULL COMMENT '证件类型',
    `address` text DEFAULT NULL COMMENT '地址',
    `company` varchar(100) DEFAULT NULL COMMENT '公司名称',
    `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户表';

-- 3. 创建项目主表
CREATE TABLE IF NOT EXISTS `project_headers` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `hid` varchar(20) NOT NULL COMMENT '项目编号（如H20240702001）',
    `desc` varchar(200) DEFAULT NULL COMMENT '项目描述',
    `company_id` int(11) DEFAULT NULL COMMENT '客户公司ID',
    `company_name` varchar(100) DEFAULT NULL COMMENT '公司名称',
    `limit` varchar(50) DEFAULT NULL COMMENT '额度限制',
    `contact` varchar(50) DEFAULT NULL COMMENT '联系人',
    `dept` varchar(50) DEFAULT NULL COMMENT '部门',
    `staff_id` int(11) DEFAULT NULL COMMENT '经办人ID',
    `staff_name` varchar(50) DEFAULT NULL COMMENT '经办人姓名',
    `currency` varchar(10) DEFAULT NULL COMMENT '币种',
    `type` varchar(50) DEFAULT NULL COMMENT '类型',
    `source` varchar(50) DEFAULT NULL COMMENT '来源',
    `country` varchar(50) DEFAULT NULL COMMENT '国家',
    `status` enum('draft','active','completed','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    `last_updated_by` varchar(50) DEFAULT NULL COMMENT '最后操作人',
    `remarks` text DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_hid` (`hid`),
    KEY `idx_company_id` (`company_id`),
    KEY `idx_status` (`status`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_project_headers_company` FOREIGN KEY (`company_id`) REFERENCES `customer_companies` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目主表';

-- 4. 创建项目REF表
CREATE TABLE IF NOT EXISTS `project_refs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `header_id` int(11) NOT NULL COMMENT 'HID主表ID',
    `ref_number` varchar(30) NOT NULL COMMENT 'REF编号',
    `name` varchar(100) DEFAULT NULL COMMENT 'REF订单名称',
    `ref_type_id` int(11) NOT NULL COMMENT 'REF类型ID',
    `description` varchar(200) NOT NULL COMMENT '描述',
    `supplier_id` int(11) DEFAULT NULL COMMENT '供应商ID',
    `supplier_contact` varchar(50) DEFAULT NULL COMMENT '供应商联系人',
    `supplier_phone` varchar(20) DEFAULT NULL COMMENT '供应商联系电话',
    `selling_price` decimal(10,2) DEFAULT NULL COMMENT '销售价格',
    `cost_price` decimal(10,2) DEFAULT NULL COMMENT '成本价格',
    `currency` varchar(3) NOT NULL DEFAULT 'SGD' COMMENT '货币类型',
    `expected_delivery_date` date DEFAULT NULL COMMENT '预计交付日期',
    `actual_delivery_date` date DEFAULT NULL COMMENT '实际交付日期',
    `remarks` text DEFAULT NULL COMMENT '备注',
    `attachments` text DEFAULT NULL COMMENT '附件列表(JSON)',
    `status` enum('draft','processing','completed','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
    `payment_status` enum('unpaid','partial','paid','refunded') NOT NULL DEFAULT 'unpaid' COMMENT '支付状态',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_ref_number` (`ref_number`),
    KEY `idx_header_id` (`header_id`),
    KEY `idx_ref_type_id` (`ref_type_id`),
    KEY `idx_supplier_id` (`supplier_id`),
    KEY `idx_status` (`status`),
    KEY `idx_payment_status` (`payment_status`),
    CONSTRAINT `fk_project_refs_header` FOREIGN KEY (`header_id`) REFERENCES `project_headers` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_project_refs_type` FOREIGN KEY (`ref_type_id`) REFERENCES `business_types` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_project_refs_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目REF表';

-- 5. 创建项目EO表
CREATE TABLE IF NOT EXISTS `project_eos` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ref_id` int(11) NOT NULL COMMENT 'REF明细ID',
    `eo_number` varchar(30) NOT NULL COMMENT 'EO编号',
    `name` varchar(100) DEFAULT NULL COMMENT 'EO订单名称',
    `supplier_type` enum('visa','flight','hotel','transport','local_operator','other') NOT NULL COMMENT '供应商类型',
    `supplier_id` int(11) NOT NULL COMMENT '供应商ID',
    `external_system` varchar(50) DEFAULT NULL COMMENT '外部系统名称',
    `external_status` varchar(50) DEFAULT NULL COMMENT '外部系统状态',
    `external_reference` varchar(100) DEFAULT NULL COMMENT '外部系统参考号',
    `amount` decimal(10,2) NOT NULL COMMENT '金额',
    `currency` varchar(3) NOT NULL DEFAULT 'SGD' COMMENT '货币类型',
    `remarks` text DEFAULT NULL COMMENT '备注',
    `status` enum('draft','confirmed','paid','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_eo_number` (`eo_number`),
    KEY `idx_ref_id` (`ref_id`),
    KEY `idx_supplier_id` (`supplier_id`),
    KEY `idx_supplier_type` (`supplier_type`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_project_eos_ref` FOREIGN KEY (`ref_id`) REFERENCES `project_refs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_project_eos_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目EO表';

-- 6. 创建REF订单项目表
CREATE TABLE IF NOT EXISTS `ref_order_items` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ref_id` int(11) NOT NULL COMMENT 'REF ID',
    `item_name` varchar(200) NOT NULL COMMENT '项目名称',
    `quantity` int(11) NOT NULL DEFAULT 1 COMMENT '数量',
    `unit_price` decimal(10,2) NOT NULL COMMENT '单价',
    `total_price` decimal(10,2) NOT NULL COMMENT '总价',
    `remarks` text DEFAULT NULL COMMENT '备注',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_ref_id` (`ref_id`),
    CONSTRAINT `fk_ref_order_items_ref` FOREIGN KEY (`ref_id`) REFERENCES `project_refs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='REF订单项目表';

-- 7. 如果project_refs表已存在但缺少header_id字段，则添加该字段
-- 注意：这个操作需要谨慎，因为可能会影响现有数据
-- ALTER TABLE `project_refs` ADD COLUMN `header_id` int(11) NOT NULL COMMENT 'HID主表ID' AFTER `id`;
-- ALTER TABLE `project_refs` ADD CONSTRAINT `fk_project_refs_header` FOREIGN KEY (`header_id`) REFERENCES `project_headers` (`id`) ON DELETE CASCADE; 