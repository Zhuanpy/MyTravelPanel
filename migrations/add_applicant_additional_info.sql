-- 为visa_documents_request表添加applicant_additional_info字段
-- 用于存储申请人补充信息，区别于旅行社补充信息(additional_info)

ALTER TABLE visa_documents_request 
ADD COLUMN applicant_additional_info TEXT NULL COMMENT '申请人补充信息';

-- 更新现有记录的applicant_additional_info字段为NULL（可选）
-- UPDATE visa_documents_request SET applicant_additional_info = NULL WHERE applicant_additional_info IS NULL;
