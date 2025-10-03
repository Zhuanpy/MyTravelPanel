-- 为 visa_types 表添加时间字段的迁移脚本
-- 执行日期: 2024年

-- 添加创建时间字段
ALTER TABLE visa_types 
ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间';

-- 添加更新时间字段
ALTER TABLE visa_types 
ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL COMMENT '更新时间';

-- 添加有效期字段
ALTER TABLE visa_types 
ADD COLUMN valid_until DATETIME NULL COMMENT '有效期';

-- 为现有记录设置创建时间和更新时间
UPDATE visa_types 
SET created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
WHERE created_at IS NULL OR updated_at IS NULL;
