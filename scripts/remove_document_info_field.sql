-- 删除 visa_documents_request 表中的 document_info 字段
-- 因为文档信息现在通过 visa_document_documents 关联表存储

-- 首先备份现有数据（可选）
-- CREATE TABLE visa_documents_request_backup AS SELECT * FROM visa_documents_request;

-- 删除 document_info 字段
ALTER TABLE `visa_documents_request` DROP COLUMN `document_info`;

-- 验证字段已删除
DESCRIBE `visa_documents_request`;

-- 检查表结构
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'visa_documents_request' 
AND TABLE_SCHEMA = DATABASE(); 