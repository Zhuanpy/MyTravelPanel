-- ========================================
-- 为 product_itinerary 表添加图片字段
-- ========================================

USE travel_panel_new;

-- 检查表是否存在
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME = 'product_itinerary';

-- 如果表已存在，添加图片字段
ALTER TABLE product_itinerary
ADD COLUMN IF NOT EXISTS image1 VARCHAR(500) COMMENT '图片1路径' AFTER day_title,
ADD COLUMN IF NOT EXISTS image2 VARCHAR(500) COMMENT '图片2路径' AFTER image1,
ADD COLUMN IF NOT EXISTS image3 VARCHAR(500) COMMENT '图片3路径' AFTER image2;

-- 验证字段已添加
DESCRIBE product_itinerary;

-- 查看现有数据
SELECT 
    id,
    product_id,
    day_number,
    LEFT(day_title, 50) as day_title_preview,
    image1,
    image2,
    image3
FROM product_itinerary
LIMIT 5;

SELECT '✅ 图片字段添加成功！' AS Status;

