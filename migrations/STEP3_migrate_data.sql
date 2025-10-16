-- ========================================
-- 步骤 3: 数据迁移 - tour_products → travelproducts
-- 执行前确保步骤1和步骤2已成功完成！
-- ========================================

USE travel_panel_new;

-- ========================================
-- 1. 检查源数据
-- ========================================

SELECT 'Checking source data from tour_products...' AS Step;

SELECT 
    COUNT(*) AS total_records,
    COUNT(DISTINCT country) AS distinct_countries,
    COUNT(DISTINCT city) AS distinct_cities,
    MIN(created_at) AS earliest_record,
    MAX(created_at) AS latest_record
FROM tour_products;

-- 查看示例数据
SELECT * FROM tour_products LIMIT 3;

-- ========================================
-- 2. 执行数据迁移
-- ========================================

SELECT 'Starting data migration...' AS Step;

INSERT INTO travelproducts (
    product_name,
    country,
    city_name,
    product_description,
    included_services,
    excluded_services,
    base_price,
    duration_days,
    currency,
    product_status,
    created_at,
    updated_at,
    created_by
)
SELECT 
    title AS product_name,
    country,
    city AS city_name,
    itinerary AS product_description,
    included AS included_services,
    not_included AS excluded_services,
    price AS base_price,
    -- 从 duration 字段提取天数（如 "3天2晚" → 3）
    CASE 
        WHEN duration REGEXP '^[0-9]+天' THEN CAST(SUBSTRING_INDEX(duration, '天', 1) AS UNSIGNED)
        ELSE NULL 
    END AS duration_days,
    'SGD' AS currency,
    'active' AS product_status,
    created_at,
    updated_at,
    'MIGRATED_FROM_TOUR_PRODUCTS' AS created_by
FROM tour_products
WHERE NOT EXISTS (
    -- 避免重复迁移
    SELECT 1 FROM travelproducts t 
    WHERE t.product_name = tour_products.title 
    AND (t.country = tour_products.country OR (t.country IS NULL AND tour_products.country IS NULL))
    AND t.created_by = 'MIGRATED_FROM_TOUR_PRODUCTS'
);

-- ========================================
-- 3. 验证迁移结果
-- ========================================

SELECT 'Verifying migration results...' AS Step;

-- 统计迁移结果
SELECT 
    (SELECT COUNT(*) FROM tour_products) AS source_total,
    (SELECT COUNT(*) FROM travelproducts WHERE created_by = 'MIGRATED_FROM_TOUR_PRODUCTS') AS migrated_count,
    (SELECT COUNT(*) FROM travelproducts) AS target_total;

-- 对比数据示例
SELECT 'Sample migrated data:' AS Info;
SELECT 
    id,
    product_name,
    country,
    city_name,
    duration_days,
    base_price,
    currency,
    created_by,
    created_at
FROM travelproducts 
WHERE created_by = 'MIGRATED_FROM_TOUR_PRODUCTS'
ORDER BY id DESC
LIMIT 10;

-- ========================================
-- 4. 完成提示
-- ========================================

SELECT 
    '✅ Data Migration Completed!' AS Status,
    CONCAT(
        (SELECT COUNT(*) FROM travelproducts WHERE created_by = 'MIGRATED_FROM_TOUR_PRODUCTS'),
        ' records migrated from tour_products to travelproducts'
    ) AS Details,
    NOW() AS CompletedAt;

-- ========================================
-- 后续步骤（可选）
-- ========================================

-- 如果确认迁移成功，可以备份并重命名/删除 tour_products 表
-- 
-- 重命名旧表（推荐）：
-- RENAME TABLE tour_products TO tour_products_backup_20251016;
-- 
-- 或删除旧表（谨慎！确保数据已备份）：
-- DROP TABLE tour_products;

