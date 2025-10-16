-- ========================================
-- 快速修复：添加图片字段到 product_itinerary
-- ========================================
-- 执行说明：
-- 1. 如果提示字段已存在的错误，可以忽略
-- 2. 执行完后查看 DESCRIBE 结果确认字段已添加
-- ========================================

USE travel_panel_new;

-- 直接添加字段（如果字段已存在会报错，可忽略）
ALTER TABLE product_itinerary 
ADD COLUMN image1 VARCHAR(500) COMMENT '图片1路径' AFTER day_title;

ALTER TABLE product_itinerary 
ADD COLUMN image2 VARCHAR(500) COMMENT '图片2路径' AFTER image1;

ALTER TABLE product_itinerary 
ADD COLUMN image3 VARCHAR(500) COMMENT '图片3路径' AFTER image2;

-- 验证表结构
DESCRIBE product_itinerary;

SELECT '✅ 图片字段已添加！' AS Status;

