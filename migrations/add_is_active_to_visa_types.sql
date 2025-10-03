-- 添加is_active字段到visa_types表
-- 执行日期: 2024-12-19

-- 添加is_active字段，默认值为1（True）
ALTER TABLE visa_types ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1 COMMENT '是否激活（显示在外部网页）';

-- 更新现有记录的is_active字段为1（激活状态）
UPDATE visa_types SET is_active = 1 WHERE is_active IS NULL;

-- 添加索引以提高查询性能
CREATE INDEX idx_visa_types_is_active ON visa_types(is_active);
