-- 检查表重命名状态脚本
-- 用于确认哪些表已经重命名，哪些还需要重命名

-- ============================================
-- 检查表是否存在
-- ============================================
-- 检查旧表名
SELECT '旧表检查' AS '检查项', 
    CASE WHEN COUNT(*) > 0 THEN '存在' ELSE '不存在' END AS '状态',
    'product_itinerary' AS '表名'
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
    AND table_name = 'product_itinerary'

UNION ALL

SELECT '旧表检查' AS '检查项',
    CASE WHEN COUNT(*) > 0 THEN '存在' ELSE '不存在' END AS '状态',
    'product_price_variant' AS '表名'
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
    AND table_name = 'product_price_variant'

UNION ALL

-- 检查新表名
SELECT '新表检查' AS '检查项',
    CASE WHEN COUNT(*) > 0 THEN '存在' ELSE '不存在' END AS '状态',
    'package_itinerary' AS '表名'
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
    AND table_name = 'package_itinerary'

UNION ALL

SELECT '新表检查' AS '检查项',
    CASE WHEN COUNT(*) > 0 THEN '存在' ELSE '不存在' END AS '状态',
    'package_price_variant' AS '表名'
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
    AND table_name = 'package_price_variant';

-- ============================================
-- 检查外键约束状态
-- ============================================
SELECT 
    TABLE_NAME AS '表名',
    CONSTRAINT_NAME AS '外键约束名称',
    COLUMN_NAME AS '列名',
    REFERENCED_TABLE_NAME AS '引用表名',
    CASE 
        WHEN CONSTRAINT_NAME LIKE 'fk_package_%' THEN '新命名'
        WHEN CONSTRAINT_NAME LIKE '%ibfk_%' THEN '旧命名（需要更新）'
        ELSE '其他'
    END AS '命名状态'
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_NAME IN ('package_itinerary', 'package_price_variant', 'product_itinerary', 'product_price_variant')
    AND COLUMN_NAME = 'product_id' 
    AND (REFERENCED_TABLE_NAME = 'package_products' OR REFERENCED_TABLE_NAME = 'travelproducts')
ORDER BY TABLE_NAME, CONSTRAINT_NAME;







