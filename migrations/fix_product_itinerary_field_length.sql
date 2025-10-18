-- ========================================
-- 修复 product_itinerary 表字段长度
-- 将 day_title 从 TEXT 改为 LONGTEXT，支持更长的行程内容
-- ========================================

USE travelindustry;

-- 查看当前表结构
DESCRIBE product_itinerary;

-- 修改 day_title 字段类型为 LONGTEXT（支持 4GB 的文本）
ALTER TABLE product_itinerary 
MODIFY COLUMN day_title LONGTEXT NOT NULL COMMENT '行程安排（支持长文本）';

-- 同时确保图片路径字段足够长
ALTER TABLE product_itinerary 
MODIFY COLUMN image1 VARCHAR(1000) COMMENT '图片1路径',
MODIFY COLUMN image2 VARCHAR(1000) COMMENT '图片2路径',
MODIFY COLUMN image3 VARCHAR(1000) COMMENT '图片3路径';

-- 验证修改后的表结构
DESCRIBE product_itinerary;

SELECT '✅ product_itinerary 表字段长度修复完成！' AS Status;
