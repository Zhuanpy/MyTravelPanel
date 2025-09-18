-- 银行关键词系统 SQL 脚本
-- 创建时间: 2024-12-19
-- 描述: 创建银行关键词管理相关表，替代txt文件读取方式

-- =============================================
-- 1. 创建银行关键词表
-- =============================================
CREATE TABLE IF NOT EXISTS `bank_statements_keywords` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `bank_name` VARCHAR(50) NOT NULL COMMENT '银行名称',
    `keyword_type` VARCHAR(50) NOT NULL COMMENT '关键词类型：personal_business, business, personal, other',
    `keyword` VARCHAR(200) NOT NULL COMMENT '关键词内容',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '关键词描述',
    `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- =============================================
-- 2. 创建银行关键词分类表
-- =============================================
CREATE TABLE IF NOT EXISTS `bank_keyword_categories` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `bank_name` VARCHAR(50) NOT NULL COMMENT '银行名称',
    `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
    `category_type` VARCHAR(50) NOT NULL COMMENT '分类类型：personal_business, business, personal, other',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '分类描述',
    `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- =============================================
-- 3. 创建索引
-- =============================================

-- 银行关键词表索引
CREATE INDEX IF NOT EXISTS `idx_bank_type` ON `bank_statements_keywords` (`bank_name`, `keyword_type`);
CREATE INDEX IF NOT EXISTS `idx_keyword` ON `bank_statements_keywords` (`keyword`);
CREATE UNIQUE INDEX IF NOT EXISTS `uq_bank_keyword` ON `bank_statements_keywords` (`bank_name`, `keyword`);

-- 银行关键词分类表索引
CREATE INDEX IF NOT EXISTS `idx_bank_category` ON `bank_keyword_categories` (`bank_name`, `category_type`);
CREATE UNIQUE INDEX IF NOT EXISTS `uq_bank_category` ON `bank_keyword_categories` (`bank_name`, `category_name`);

-- =============================================
-- 4. 插入示例数据
-- =============================================

-- UOB 银行关键词
INSERT INTO `bank_statements_keywords` (`bank_name`, `keyword_type`, `keyword`, `description`, `is_active`) VALUES
-- 个人商用关键词
('UOB', 'personal_business', 'PAYNOW-FAST', 'PayNow快速支付', 1),
('UOB', 'personal_business', 'BUS/MRT', '公共交通', 1),
('UOB', 'personal_business', 'MIXUE', '蜜雪冰城', 1),
('UOB', 'personal_business', 'GRAB', 'Grab打车', 1),
('UOB', 'personal_business', 'TAXI', '出租车', 1),
('UOB', 'personal_business', 'FUEL', '加油', 1),

-- 商业关键词
('UOB', 'business', 'OFFICE RENT', '办公室租金', 1),
('UOB', 'business', 'UTILITIES', '水电费', 1),
('UOB', 'business', 'SUPPLIER', '供应商付款', 1),
('UOB', 'business', 'STAFF SALARY', '员工工资', 1),
('UOB', 'business', 'INSURANCE', '保险费用', 1),
('UOB', 'business', 'MARKETING', '营销费用', 1),

-- 个人消费关键词
('UOB', 'personal', 'SHOPPING', '购物', 1),
('UOB', 'personal', 'FOOD', '餐饮', 1),
('UOB', 'personal', 'ENTERTAINMENT', '娱乐', 1),
('UOB', 'personal', 'HEALTHCARE', '医疗', 1),
('UOB', 'personal', 'EDUCATION', '教育', 1);

-- OCBC 银行关键词
INSERT INTO `bank_statements_keywords` (`bank_name`, `keyword_type`, `keyword`, `description`, `is_active`) VALUES
-- 个人商用关键词
('OCBC', 'personal_business', 'PAYNOW', 'PayNow支付', 1),
('OCBC', 'personal_business', 'NETS', 'NETS支付', 1),
('OCBC', 'personal_business', 'TRANSPORT', '交通费用', 1),

-- 商业关键词
('OCBC', 'business', 'RENT', '租金', 1),
('OCBC', 'business', 'UTILITIES', '水电费', 1),
('OCBC', 'business', 'SUPPLIER', '供应商', 1),
('OCBC', 'business', 'SALARY', '工资', 1),

-- 个人消费关键词
('OCBC', 'personal', 'DINING', '用餐', 1),
('OCBC', 'personal', 'SHOPPING', '购物', 1),
('OCBC', 'personal', 'LEISURE', '休闲', 1);

-- 招商银行关键词
INSERT INTO `bank_statements_keywords` (`bank_name`, `keyword_type`, `keyword`, `description`, `is_active`) VALUES
-- 个人商用关键词
('CMB', 'personal_business', '微信支付', '微信支付', 1),
('CMB', 'personal_business', '支付宝', '支付宝', 1),
('CMB', 'personal_business', '交通', '交通费用', 1),

-- 商业关键词
('CMB', 'business', '租金', '租金', 1),
('CMB', 'business', '水电', '水电费', 1),
('CMB', 'business', '供应商', '供应商付款', 1),
('CMB', 'business', '工资', '员工工资', 1),

-- 个人消费关键词
('CMB', 'personal', '餐饮', '餐饮', 1),
('CMB', 'personal', '购物', '购物', 1),
('CMB', 'personal', '娱乐', '娱乐', 1);

-- =============================================
-- 5. 插入关键词分类数据
-- =============================================

INSERT INTO `bank_keyword_categories` (`bank_name`, `category_name`, `category_type`, `description`, `is_active`) VALUES
-- UOB 分类
('UOB', '个人商用', 'personal_business', '个人商业用途的消费', 1),
('UOB', '商业支出', 'business', '公司/企业相关支出', 1),
('UOB', '个人消费', 'personal', '纯个人生活消费', 1),
('UOB', '其他', 'other', '其他分类', 1),

-- OCBC 分类
('OCBC', '个人商用', 'personal_business', '个人商业用途的消费', 1),
('OCBC', '商业支出', 'business', '公司/企业相关支出', 1),
('OCBC', '个人消费', 'personal', '纯个人生活消费', 1),
('OCBC', '其他', 'other', '其他分类', 1),

-- 招商银行分类
('CMB', '个人商用', 'personal_business', '个人商业用途的消费', 1),
('CMB', '商业支出', 'business', '公司/企业相关支出', 1),
('CMB', '个人消费', 'personal', '纯个人生活消费', 1),
('CMB', '其他', 'other', '其他分类', 1);

-- =============================================
-- 6. 创建触发器（自动更新 updated_at）
-- =============================================

-- 银行关键词表触发器
CREATE TRIGGER IF NOT EXISTS `update_bank_statements_keywords_updated_at`
    AFTER UPDATE ON `bank_statements_keywords`
    FOR EACH ROW
BEGIN
    UPDATE `bank_statements_keywords` 
    SET `updated_at` = CURRENT_TIMESTAMP 
    WHERE `id` = NEW.`id`;
END;

-- =============================================
-- 7. 查询验证
-- =============================================

-- 查看表结构
-- .schema bank_statements_keywords
-- .schema bank_keyword_categories

-- 查看数据统计
-- SELECT bank_name, keyword_type, COUNT(*) as count 
-- FROM bank_statements_keywords 
-- GROUP BY bank_name, keyword_type 
-- ORDER BY bank_name, keyword_type;

-- 查看所有关键词
-- SELECT * FROM bank_statements_keywords ORDER BY bank_name, keyword_type, keyword;

-- =============================================
-- 8. 使用说明
-- =============================================

/*
使用说明：

1. 执行此SQL脚本创建表结构：
   sqlite3 your_database.db < bank_keywords_sql.sql

2. 访问关键词管理页面：
   http://127.0.0.1:5000/statement/keywords

3. 关键词类型说明：
   - personal_business: 个人商用（个人商业用途的消费）
   - business: 商业（公司/企业相关支出）
   - personal: 个人消费（纯个人生活消费）
   - other: 其他分类

4. 支持的银行：
   - UOB: 大华银行
   - OCBC: 华侨银行
   - CMB: 招商银行
   - 可扩展其他银行

5. 关键词匹配规则：
   - 区分大小写
   - 部分匹配（包含关系）
   - 支持多个关键词同时匹配

6. 管理功能：
   - 添加/编辑/删除关键词
   - 批量导入（JSON格式）
   - 从txt文件导入（兼容原有方式）
   - 按银行和类型筛选
   - 导出功能
*/
