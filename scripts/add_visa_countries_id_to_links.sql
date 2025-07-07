-- 添加 visa_countries_id 字段到 visa_type_links 表
-- 执行时间: 2025-07-06

-- 1. 添加新字段
ALTER TABLE visa_type_links 
ADD COLUMN visa_countries_id INTEGER;

-- 2. 添加外键约束
ALTER TABLE visa_type_links 
ADD CONSTRAINT fk_visa_links_countries 
FOREIGN KEY (visa_countries_id) 
REFERENCES visa_countries(id) 
ON DELETE CASCADE;

-- 3. 创建索引以提高查询性能
CREATE INDEX idx_visa_links_countries_id 
ON visa_type_links(visa_countries_id);

-- 4. 可选：根据现有的 visa_type_id 更新 visa_countries_id
-- 这个查询会将 visa_type_links 表中的 visa_countries_id 设置为对应的国家ID
UPDATE visa_type_links 
SET visa_countries_id = (
    SELECT vt.country_id 
    FROM visa_types vt 
    WHERE vt.id = visa_type_links.visa_type_id
)
WHERE visa_countries_id IS NULL;

-- 5. 验证更新结果
SELECT 
    vtl.id,
    vtl.name,
    vtl.visa_type_id,
    vtl.visa_countries_id,
    vc.country_name_CN as country_name
FROM visa_type_links vtl
LEFT JOIN visa_countries vc ON vtl.visa_countries_id = vc.id
ORDER BY vtl.id; 