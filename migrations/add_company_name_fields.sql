-- ========================================
-- 为 company_info 表添加公司简称和中文名字段
-- ========================================

USE travelindustry;

-- 查看当前表结构
DESCRIBE company_info;

-- 添加公司中文名字字段
ALTER TABLE company_info 
ADD COLUMN company_name_cn VARCHAR(100) COMMENT '公司中文名' AFTER company_name;

-- 添加公司简称字段
ALTER TABLE company_info 
ADD COLUMN company_short_name VARCHAR(50) COMMENT '公司简称' AFTER company_name_cn;

-- 查看更新后的表结构
DESCRIBE company_info;

-- 如果有现有数据，可以设置默认值
-- UPDATE company_info 
-- SET company_name_cn = '悦行假期有限公司',
--     company_short_name = '悦行假期'
-- WHERE id > 0;

SELECT '✅ company_info 表字段添加完成！' AS Status;

-- 新增字段说明：
-- company_name: 公司英文名/全称（原有字段，如：JOYFUL ESCAPES PTE LTD）
-- company_name_cn: 公司中文名（新增，如：悦行假期有限公司）
-- company_short_name: 公司简称（新增，如：悦行假期）

