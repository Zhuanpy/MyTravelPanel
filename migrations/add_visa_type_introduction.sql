-- 为visa_types表添加签证说明字段
ALTER TABLE visa_types 
ADD COLUMN introduction TEXT NULL COMMENT '签证说明';
