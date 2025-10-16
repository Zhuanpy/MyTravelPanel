-- ========================================
-- 调试：检查当前数据状态
-- ========================================

USE travel_panel_new;

-- 1. 检查 travelproducts 表是否有数据
SELECT '1. Checking travelproducts table...' AS Info;
SELECT COUNT(*) AS total_records FROM travelproducts;

-- 2. 查看 travelproducts 的所有记录
SELECT '2. All travelproducts records:' AS Info;
SELECT 
    id,
    supplier_id,
    product_name,
    country,
    city_name,
    duration_days,
    base_price,
    product_status,
    created_by
FROM travelproducts;

-- 3. 检查新字段是否存在
SELECT '3. Checking if new columns exist...' AS Info;
SHOW COLUMNS FROM travelproducts LIKE 'supplier_id';
SHOW COLUMNS FROM travelproducts LIKE 'country';
SHOW COLUMNS FROM travelproducts LIKE 'cover_image';

-- 4. 检查 tour_products 表的数据
SELECT '4. Checking tour_products table...' AS Info;
SELECT COUNT(*) AS total_records FROM tour_products;

SELECT 
    id,
    title,
    country,
    city,
    duration,
    price
FROM tour_products
LIMIT 10;

-- 5. 检查是否已执行过数据迁移
SELECT '5. Checking if data migration was executed...' AS Info;
SELECT COUNT(*) AS migrated_records 
FROM travelproducts 
WHERE created_by = 'MIGRATED_FROM_TOUR_PRODUCTS';

-- 6. 如果 travelproducts 为空，显示迁移命令
SELECT '6. If travelproducts is empty, run STEP3_migrate_data.sql' AS Info;

