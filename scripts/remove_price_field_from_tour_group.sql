-- 移除 TourGroup 表中的 price 字段
-- 执行日期: 2025-01-27

-- 检查字段是否存在
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'tour_group' 
AND column_name = 'price';

-- 如果字段存在，则移除
ALTER TABLE tour_group DROP COLUMN IF EXISTS price;

-- 验证字段已移除
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'tour_group' 
ORDER BY ordinal_position; 