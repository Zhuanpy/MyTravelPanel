-- 为tour_group表添加price字段
-- 执行日期: 2025-01-XX

-- 添加报价字段
ALTER TABLE tour_group ADD COLUMN price FLOAT COMMENT '报价（新币）';

-- 验证字段是否添加成功
DESCRIBE tour_group; 