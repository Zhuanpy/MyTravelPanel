-- 重新创建 Athina 表结构 SQL 语句
-- 删除现有表并创建新的表结构

-- 1. 删除现有表（如果存在）
-- 注意：这会删除所有现有数据！
DROP TABLE IF EXISTS `athina_booking_details`;
DROP TABLE IF EXISTS `athina_booking_headers`;

-- 2. 创建 athina_booking_headers 表（头部表 - 包含汇总数据）
CREATE TABLE `athina_booking_headers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `booking_header_id` varchar(50) NOT NULL COMMENT '预订头部ID',
  `corporate_name` varchar(200) DEFAULT NULL COMMENT '公司名称',
  `book_date` date DEFAULT NULL COMMENT '预订日期',
  
  -- 汇总财务数据
  `sub_total_gross` decimal(15,2) DEFAULT NULL COMMENT '小计总金额',
  `sub_total_cost` decimal(15,2) DEFAULT NULL COMMENT '小计成本',
  `sub_total_pl` decimal(15,2) DEFAULT NULL COMMENT '小计盈亏',
  `sub_total_balance` decimal(15,2) DEFAULT NULL COMMENT '小计余额',
  `sub_total_tax` decimal(15,2) DEFAULT NULL COMMENT '小计税额',
  `sub_total_discount` decimal(15,2) DEFAULT NULL COMMENT '小计折扣',
  `sub_total_local_gross` decimal(15,2) DEFAULT NULL COMMENT '小计本地总金额',
  `sub_total_margin` decimal(5,2) DEFAULT NULL COMMENT '小计利润率',
  
  -- 顾问和发票信息
  `consultant` varchar(200) DEFAULT NULL COMMENT '顾问',
  `sales_consultant` varchar(200) DEFAULT NULL COMMENT '销售顾问',
  `invoice_no` varchar(100) DEFAULT NULL COMMENT '发票号',
  `invoice_date` date DEFAULT NULL COMMENT '发票日期',
  
  -- 时间戳
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `booking_header_id` (`booking_header_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Athina 预订头部信息 - 包含汇总数据';

-- 3. 创建 athina_booking_details 表（明细表 - 包含所有业务和财务数据）
CREATE TABLE `athina_booking_details` (
  `id` int NOT NULL AUTO_INCREMENT,
  `header_id` int NOT NULL COMMENT '头部ID',
  
  -- 业务信息
  `corporate_name` varchar(200) DEFAULT NULL COMMENT '公司名称',
  `client_name` varchar(200) DEFAULT NULL COMMENT '客户名称',
  `booking_ref` varchar(100) DEFAULT NULL COMMENT '预订参考号',
  `book_type` varchar(50) DEFAULT NULL COMMENT '预订类型',
  `book_date` date DEFAULT NULL COMMENT '预订日期',
  `dep_date` date DEFAULT NULL COMMENT '出发日期',
  `itin_desc` text COMMENT '行程描述',
  
  -- 财务信息
  `gross_curr` varchar(10) DEFAULT NULL COMMENT '总金额货币',
  `gross_amount` decimal(15,2) DEFAULT NULL COMMENT '总金额',
  `gross_tax` decimal(15,2) DEFAULT NULL COMMENT '总税额',
  `discount` decimal(15,2) DEFAULT NULL COMMENT '折扣',
  `local_gross` decimal(15,2) DEFAULT NULL COMMENT '本地总金额',
  `local_cost` decimal(15,2) DEFAULT NULL COMMENT '本地成本',
  `profit_loss` decimal(15,2) DEFAULT NULL COMMENT '盈亏',
  `margin` decimal(5,2) DEFAULT NULL COMMENT '利润率',
  `balance` decimal(15,2) DEFAULT NULL COMMENT '余额',
  
  -- 供应商信息
  `supplier` varchar(200) DEFAULT NULL COMMENT '供应商',
  `consultant` varchar(200) DEFAULT NULL COMMENT '顾问',
  `sales_consultant` varchar(200) DEFAULT NULL COMMENT '销售顾问',
  
  -- 发票信息
  `invoice_no` varchar(100) DEFAULT NULL COMMENT '发票号',
  `invoice_date` date DEFAULT NULL COMMENT '发票日期',
  
  -- 特殊标记
  `is_subtotal` tinyint(1) DEFAULT '0' COMMENT '是否为小计行',
  
  -- 时间戳
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  KEY `header_id` (`header_id`),
  CONSTRAINT `athina_booking_details_ibfk_1` FOREIGN KEY (`header_id`) REFERENCES `athina_booking_headers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Athina 预订明细信息 - 包含所有业务和财务数据';

-- 4. 验证表结构
-- 查看创建的表
SHOW TABLES LIKE 'athina_%';

-- 查看 athina_booking_headers 表结构
DESCRIBE `athina_booking_headers`;

-- 查看 athina_booking_details 表结构
DESCRIBE `athina_booking_details`;

-- 5. 显示表创建成功信息
SELECT 'Athina 表结构创建完成！' AS message;
