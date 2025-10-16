-- ========================================
-- 检查 product_references 表是否存在
-- ========================================

USE travel_panel_new;

-- 检查表是否存在
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND TABLE_NAME = 'product_references';

-- 如果表存在，查看表结构
-- DESCRIBE product_references;

-- 如果表存在，查看数据
-- SELECT * FROM product_references LIMIT 5;

-- 查看所有包含 'product' 或 'reference' 的表
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'travel_panel_new' 
    AND (TABLE_NAME LIKE '%product%' OR TABLE_NAME LIKE '%reference%')
ORDER BY TABLE_NAME;

