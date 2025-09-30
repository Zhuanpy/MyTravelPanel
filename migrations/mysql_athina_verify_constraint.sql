-- MySQL Athina表唯一约束验证脚本
-- 验证booking_ref唯一约束是否正常工作

-- ========================================
-- 1. 检查约束详情
-- ========================================
SELECT 
    '约束信息' as info_type,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME,
    ORDINAL_POSITION
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME LIKE '%booking_ref%'
ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION;

-- ========================================
-- 2. 检查唯一索引
-- ========================================
SELECT 
    '索引信息' as info_type,
    INDEX_NAME,
    NON_UNIQUE,
    COLUMN_NAME
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND COLUMN_NAME = 'booking_ref'
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- ========================================
-- 3. 检查重复记录
-- ========================================
SELECT 
    '重复记录检查' as info_type,
    booking_ref, 
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY created_at DESC) as record_ids
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- ========================================
-- 4. 测试约束功能
-- ========================================
-- 尝试插入重复的booking_ref（应该失败）
-- 选择一个已存在的booking_ref进行测试
SET @test_ref = (SELECT booking_ref FROM athina_booking_details WHERE booking_ref IS NOT NULL LIMIT 1);

SELECT CONCAT('使用测试引用: ', COALESCE(@test_ref, 'NULL')) as test_info;

-- 如果找到了测试引用，尝试插入重复数据
INSERT INTO athina_booking_details (header_id, booking_ref, client_name) 
VALUES (1, @test_ref, 'Test Duplicate Client');

-- 如果上面的INSERT成功，说明约束没有工作
-- 如果失败，说明约束正常工作

-- ========================================
-- 5. 清理测试数据（如果插入成功的话）
-- ========================================
DELETE FROM athina_booking_details 
WHERE booking_ref = @test_ref 
    AND client_name = 'Test Duplicate Client';

-- ========================================
-- 6. 统计信息
-- ========================================
SELECT 
    '数据统计' as info_type,
    '总记录数' as metric,
    COUNT(*) as value
FROM athina_booking_details

UNION ALL

SELECT 
    '数据统计' as info_type,
    '有效booking_ref数' as metric,
    COUNT(DISTINCT booking_ref) as value
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL

UNION ALL

SELECT 
    '数据统计' as info_type,
    'NULL booking_ref数' as metric,
    COUNT(*) as value
FROM athina_booking_details 
WHERE booking_ref IS NULL;

-- ========================================
-- 7. 最终验证结果
-- ========================================
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM athina_booking_details WHERE booking_ref IS NOT NULL GROUP BY booking_ref HAVING COUNT(*) > 1) = 0 
        THEN '✅ 约束验证成功：没有重复的booking_ref'
        ELSE '❌ 约束验证失败：仍有重复的booking_ref'
    END as final_result;
