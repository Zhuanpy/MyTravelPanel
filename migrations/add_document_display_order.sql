-- 为visa_document_documents表添加显示顺序字段
ALTER TABLE visa_document_documents 
ADD COLUMN display_order INT DEFAULT 0 COMMENT '显示顺序';
