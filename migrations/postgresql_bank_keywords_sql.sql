-- 银行关键词系统 PostgreSQL SQL 脚本
-- 创建时间: 2024-12-19
-- 描述: 创建银行关键词管理相关表，替代txt文件读取方式
-- 适用于: PostgreSQL 12+

-- =============================================
-- 1. 创建银行关键词表
-- =============================================
CREATE TABLE IF NOT EXISTS bank_statements_keywords (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(50) NOT NULL,
    keyword_type VARCHAR(50) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_bank_keyword UNIQUE (bank_name, keyword)
);

-- =============================================
-- 2. 创建银行关键词分类表
-- =============================================
CREATE TABLE IF NOT EXISTS bank_keyword_categories (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(50) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    category_type VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_bank_category UNIQUE (bank_name, category_name)
);

-- =============================================
-- 3. 创建索引
-- =============================================

-- 银行关键词表索引
CREATE INDEX IF NOT EXISTS idx_bank_statements_keywords_bank_type 
    ON bank_statements_keywords (bank_name, keyword_type);
CREATE INDEX IF NOT EXISTS idx_bank_statements_keywords_keyword 
    ON bank_statements_keywords (keyword);

-- 银行关键词分类表索引
CREATE INDEX IF NOT EXISTS idx_bank_keyword_categories_bank_category 
    ON bank_keyword_categories (bank_name, category_type);

-- =============================================
-- 4. 创建触发器函数（自动更新 updated_at）
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 银行关键词表触发器
CREATE TRIGGER update_bank_statements_keywords_updated_at
    BEFORE UPDATE ON bank_statements_keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 5. 添加表注释
-- =============================================

COMMENT ON TABLE bank_statements_keywords IS '银行关键词表';
COMMENT ON COLUMN bank_statements_keywords.bank_name IS '银行名称';
COMMENT ON COLUMN bank_statements_keywords.keyword_type IS '关键词类型：personal_business, business, personal, other';
COMMENT ON COLUMN bank_statements_keywords.keyword IS '关键词内容';
COMMENT ON COLUMN bank_statements_keywords.description IS '关键词描述';
COMMENT ON COLUMN bank_statements_keywords.is_active IS '是否启用';
COMMENT ON COLUMN bank_statements_keywords.created_at IS '创建时间';
COMMENT ON COLUMN bank_statements_keywords.updated_at IS '更新时间';

COMMENT ON TABLE bank_keyword_categories IS '银行关键词分类表';
COMMENT ON COLUMN bank_keyword_categories.bank_name IS '银行名称';
COMMENT ON COLUMN bank_keyword_categories.category_name IS '分类名称';
COMMENT ON COLUMN bank_keyword_categories.category_type IS '分类类型：personal_business, business, personal, other';
COMMENT ON COLUMN bank_keyword_categories.description IS '分类描述';
COMMENT ON COLUMN bank_keyword_categories.is_active IS '是否启用';
COMMENT ON COLUMN bank_keyword_categories.created_at IS '创建时间';

-- =============================================
-- 6. 插入示例数据
-- =============================================

-- UOB 银行关键词
INSERT INTO bank_statements_keywords (bank_name, keyword_type, keyword, description, is_active) VALUES
-- 个人商用关键词
('UOB', 'personal_business', 'PAYNOW-FAST', 'PayNow快速支付', TRUE),
('UOB', 'personal_business', 'BUS/MRT', '公共交通', TRUE),
('UOB', 'personal_business', 'MIXUE', '蜜雪冰城', TRUE),
('UOB', 'personal_business', 'GRAB', 'Grab打车', TRUE),
('UOB', 'personal_business', 'TAXI', '出租车', TRUE),
('UOB', 'personal_business', 'FUEL', '加油', TRUE),

-- 商业关键词
('UOB', 'business', 'OFFICE RENT', '办公室租金', TRUE),
('UOB', 'business', 'UTILITIES', '水电费', TRUE),
('UOB', 'business', 'SUPPLIER', '供应商付款', TRUE),
('UOB', 'business', 'STAFF SALARY', '员工工资', TRUE),
('UOB', 'business', 'INSURANCE', '保险费用', TRUE),
('UOB', 'business', 'MARKETING', '营销费用', TRUE),

-- 个人消费关键词
('UOB', 'personal', 'SHOPPING', '购物', TRUE),
('UOB', 'personal', 'FOOD', '餐饮', TRUE),
('UOB', 'personal', 'ENTERTAINMENT', '娱乐', TRUE),
('UOB', 'personal', 'HEALTHCARE', '医疗', TRUE),
('UOB', 'personal', 'EDUCATION', '教育', TRUE);

-- OCBC 银行关键词
INSERT INTO bank_statements_keywords (bank_name, keyword_type, keyword, description, is_active) VALUES
-- 个人商用关键词
('OCBC', 'personal_business', 'PAYNOW', 'PayNow支付', TRUE),
('OCBC', 'personal_business', 'NETS', 'NETS支付', TRUE),
('OCBC', 'personal_business', 'TRANSPORT', '交通费用', TRUE),

-- 商业关键词
('OCBC', 'business', 'RENT', '租金', TRUE),
('OCBC', 'business', 'UTILITIES', '水电费', TRUE),
('OCBC', 'business', 'SUPPLIER', '供应商', TRUE),
('OCBC', 'business', 'SALARY', '工资', TRUE),

-- 个人消费关键词
('OCBC', 'personal', 'DINING', '用餐', TRUE),
('OCBC', 'personal', 'SHOPPING', '购物', TRUE),
('OCBC', 'personal', 'LEISURE', '休闲', TRUE);

-- 招商银行关键词
INSERT INTO bank_statements_keywords (bank_name, keyword_type, keyword, description, is_active) VALUES
-- 个人商用关键词
('CMB', 'personal_business', '微信支付', '微信支付', TRUE),
('CMB', 'personal_business', '支付宝', '支付宝', TRUE),
('CMB', 'personal_business', '交通', '交通费用', TRUE),

-- 商业关键词
('CMB', 'business', '租金', '租金', TRUE),
('CMB', 'business', '水电', '水电费', TRUE),
('CMB', 'business', '供应商', '供应商付款', TRUE),
('CMB', 'business', '工资', '员工工资', TRUE),

-- 个人消费关键词
('CMB', 'personal', '餐饮', '餐饮', TRUE),
('CMB', 'personal', '购物', '购物', TRUE),
('CMB', 'personal', '娱乐', '娱乐', TRUE);

-- =============================================
-- 7. 插入关键词分类数据
-- =============================================

INSERT INTO bank_keyword_categories (bank_name, category_name, category_type, description, is_active) VALUES
-- UOB 分类
('UOB', '个人商用', 'personal_business', '个人商业用途的消费', TRUE),
('UOB', '商业支出', 'business', '公司/企业相关支出', TRUE),
('UOB', '个人消费', 'personal', '纯个人生活消费', TRUE),
('UOB', '其他', 'other', '其他分类', TRUE),

-- OCBC 分类
('OCBC', '个人商用', 'personal_business', '个人商业用途的消费', TRUE),
('OCBC', '商业支出', 'business', '公司/企业相关支出', TRUE),
('OCBC', '个人消费', 'personal', '纯个人生活消费', TRUE),
('OCBC', '其他', 'other', '其他分类', TRUE),

-- 招商银行分类
('CMB', '个人商用', 'personal_business', '个人商业用途的消费', TRUE),
('CMB', '商业支出', 'business', '公司/企业相关支出', TRUE),
('CMB', '个人消费', 'personal', '纯个人生活消费', TRUE),
('CMB', '其他', 'other', '其他分类', TRUE);

-- =============================================
-- 8. 查询验证
-- =============================================

-- 查看表结构
-- \d bank_statements_keywords
-- \d bank_keyword_categories

-- 查看数据统计
-- SELECT bank_name, keyword_type, COUNT(*) as count 
-- FROM bank_statements_keywords 
-- GROUP BY bank_name, keyword_type 
-- ORDER BY bank_name, keyword_type;

-- 查看所有关键词
-- SELECT * FROM bank_statements_keywords ORDER BY bank_name, keyword_type, keyword;

-- =============================================
-- 9. 使用说明
-- =============================================

/*
使用说明：

1. 执行此SQL脚本创建表结构：
   psql -U username -d database_name -f postgresql_bank_keywords_sql.sql

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

7. PostgreSQL 特性：
   - 使用 SERIAL 自增主键
   - 支持触发器自动更新 updated_at
   - 完整的约束和索引
   - 详细的表注释
*/

