-- ========================================
-- 检查 product_price_variant 表是否存在及使用情况
-- ========================================

USE travel_panel_new;

-- 1. 检查表是否存在
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    UPDATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME = 'product_price_variant';

-- 2. 如果表存在，查看表结构
DESCRIBE product_price_variant;

-- 3. 如果表存在，查看数据样本
SELECT * FROM product_price_variant LIMIT 5;

-- 4. 如果表存在，统计数据量
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT product_id) as unique_products,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM product_price_variant;

-- 5. 查看价格变体的分布（按产品）
SELECT 
    product_id,
    COUNT(*) as variant_count,
    MIN(adult_price) as min_price,
    MAX(adult_price) as max_price
FROM product_price_variant
GROUP BY product_id
ORDER BY variant_count DESC
LIMIT 10;

SELECT '✅ product_price_variant 表检查完成！' AS Status;

