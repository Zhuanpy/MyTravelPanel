-- 更新 visa_documents_request 表结构，将字符串字段改为外键关联
-- 执行前请备份数据库
-- 注意：这是MySQL语法

-- 0. 临时禁用安全模式
SET SQL_SAFE_UPDATES = 0;

-- 1. 添加新的外键字段
ALTER TABLE visa_documents_request 
ADD COLUMN visa_type_id_new INTEGER,
ADD COLUMN singapore_identity_id_new INTEGER;

-- 2. 更新 visa_type_id_new 字段 (MySQL语法)
UPDATE visa_documents_request vdr
JOIN visa_types vt ON vdr.visa_type = vt.visa_type
SET vdr.visa_type_id_new = vt.id
WHERE vdr.visa_type IS NOT NULL;

-- 3. 更新 singapore_identity_id_new 字段 (MySQL语法)
UPDATE visa_documents_request vdr
JOIN visa_singapore_identity vsi ON vdr.singapore_identity = vsi.identity_zh
SET vdr.singapore_identity_id_new = vsi.id
WHERE vdr.singapore_identity IS NOT NULL;

-- 4. 删除旧字段
ALTER TABLE visa_documents_request 
DROP COLUMN visa_type,
DROP COLUMN singapore_identity;

-- 5. 重命名新字段
ALTER TABLE visa_documents_request 
CHANGE COLUMN visa_type_id_new visa_type_id INTEGER;

ALTER TABLE visa_documents_request 
CHANGE COLUMN singapore_identity_id_new singapore_identity_id INTEGER;

-- 6. 添加外键约束
ALTER TABLE visa_documents_request 
ADD CONSTRAINT fk_visa_documents_visa_type 
FOREIGN KEY (visa_type_id) REFERENCES visa_types(id) ON DELETE CASCADE;

ALTER TABLE visa_documents_request 
ADD CONSTRAINT fk_visa_documents_singapore_identity 
FOREIGN KEY (singapore_identity_id) REFERENCES visa_singapore_identity(id) ON DELETE CASCADE;

-- 7. 添加索引以提高查询性能
CREATE INDEX idx_visa_documents_visa_type_id ON visa_documents_request(visa_type_id);
CREATE INDEX idx_visa_documents_singapore_identity_id ON visa_documents_request(singapore_identity_id);

-- 8. 重新启用安全模式
SET SQL_SAFE_UPDATES = 1; 