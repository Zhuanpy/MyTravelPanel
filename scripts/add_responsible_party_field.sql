-- 添加responsible_party字段到visa_documents_list表
ALTER TABLE visa_documents_list 
ADD COLUMN responsible_party VARCHAR(20) DEFAULT 'FOR_APPLICATION' COMMENT '资料准备方：FOR_APPLICATION(申请人准备)/FOR_AGENT(旅行社准备)';

-- 显示更新后的表结构
DESCRIBE visa_documents_list;

-- 添加responsible_party字段到visa_document_documents表
ALTER TABLE visa_document_documents 
ADD COLUMN responsible_party VARCHAR(20) DEFAULT 'FOR_APPLICATION' COMMENT '资料准备方：FOR_APPLICATION(申请人准备)/FOR_AGENT(旅行社准备)';

-- 显示更新后的表结构
DESCRIBE visa_document_documents; 