-- ========================================
-- 数据迁移脚本：tour_products → travelproducts
-- 日期: 2025-10-16
-- 目的: 将旧的 tour_products 表数据迁移到新的 travelproducts 表
-- ========================================

USE travel_panel_new;

-- ========================================
-- 第一步：检查数据
-- ========================================

-- 查看 tour_products 表的数据量
SELECT 'Checking tour_products data...' AS Step;
SELECT COUNT(*) AS total_records FROM tour_products;

-- 查看示例数据
SELECT * FROM tour_products LIMIT 5;

-- ========================================
-- 第二步：数据迁移
-- ========================================

-- 迁移 tour_products 数据到 travelproducts
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
    CAST(SUBSTRING_INDEX(duration, '天', 1) AS UNSIGNED) AS duration_days,
    'SGD' AS currency,
    'active' AS product_status,
    created_at,
    updated_at,
    'SYSTEM_MIGRATION' AS created_by
FROM tour_products
WHERE NOT EXISTS (
    -- 避免重复迁移
    SELECT 1 FROM travelproducts t 
    WHERE t.product_name = tour_products.title 
    AND t.country = tour_products.country
);

-- ========================================
-- 第三步：验证迁移结果
-- ========================================

-- 统计迁移的记录数
SELECT 'Migration completed. Checking results...' AS Step;

SELECT 
    (SELECT COUNT(*) FROM tour_products) AS tour_products_count,
    (SELECT COUNT(*) FROM travelproducts WHERE created_by = 'SYSTEM_MIGRATION') AS migrated_count,
    (SELECT COUNT(*) FROM travelproducts) AS total_travelproducts_count;

-- 查看迁移的数据示例
SELECT 
    id,
    product_name,
    country,
    city_name,
    duration_days,
    base_price,
    created_by
FROM travelproducts 
WHERE created_by = 'SYSTEM_MIGRATION'
ORDER BY id DESC
LIMIT 10;

-- ========================================
-- 第四步：可选 - 备份和清理
-- ========================================

-- 如果迁移成功，可以备份旧表后删除
-- 1. 先备份（建议在 MySQL Workbench 外部执行）
-- mysqldump -h localhost -u root -p travel_panel_new tour_products > tour_products_backup_20251016.sql

-- 2. 重命名旧表（保留备份）
-- RENAME TABLE tour_products TO tour_products_backup_20251016;

-- 或者直接删除（谨慎！）
-- DROP TABLE tour_products;

-- ========================================
-- 完成提示
-- ========================================

SELECT 
    '✅ Data Migration from tour_products to travelproducts Completed!' AS Status,
    NOW() AS CompletedAt;

