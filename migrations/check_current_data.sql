-- ========================================
-- 检查当前数据情况
-- ========================================

USE travel_panel_new;

-- 1. 检查 travelproducts 表的数据
SELECT 'Checking travelproducts table...' AS Step;

SELECT COUNT(*) AS total_count FROM travelproducts;

-- 查看所有记录
SELECT 
    id,
    supplier_id,
    product_name,
    country,
    city_name,
    duration_days,
    base_price,
    product_status,
    created_by,
    created_at
FROM travelproducts
ORDER BY id;

-- 2. 检查 tour_products 表的数据
SELECT 'Checking tour_products table...' AS Step;

SELECT COUNT(*) AS total_count FROM tour_products;

SELECT 
    id,
    title,
    country,
    city,
    duration,
    price,
    created_at
FROM tour_products
ORDER BY id;

-- 3. 检查哪些字段已有数据
SELECT 
    COUNT(*) AS total,
    COUNT(supplier_id) AS has_supplier,
    COUNT(product_code) AS has_code,
    COUNT(country) AS has_country,
    COUNT(cover_image) AS has_cover,
    COUNT(tags) AS has_tags,
    COUNT(created_by) AS has_creator
FROM travelproducts;

