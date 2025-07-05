-- 删除project_headers表中的company_name字段
-- 执行前请确保所有数据已正确关联到company_id

-- 1. 备份表结构（可选）
-- CREATE TABLE project_headers_backup AS SELECT * FROM project_headers;

-- 2. 删除company_name字段
ALTER TABLE project_headers DROP COLUMN company_name;

-- 3. 验证字段已删除
-- DESCRIBE project_headers;

-- 4. 验证外键约束正常工作
-- 确保company_id的外键约束正常工作 