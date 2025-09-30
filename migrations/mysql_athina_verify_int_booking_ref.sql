-- MySQL Athina表booking_ref INT类型验证脚本
-- 验证booking_ref字段类型修改后的数据完整性

-- ========================================
-- 1. 验证字段类型
-- ========================================
SELECT 
    '字段类型验证' as check_type,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_KEY,
    COLUMN_DEFAULT
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND COLUMN_NAME = 'booking_ref';

-- ========================================
-- 2. 验证唯一约束
-- ========================================
SELECT 
    '唯一约束验证' as check_type,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- ========================================
-- 3. 检查数据统计
-- ========================================
SELECT 
    '数据统计' as check_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT booking_ref) as unique_booking_refs,
    COUNT(CASE WHEN booking_ref IS NULL THEN 1 END) as null_booking_refs,
    COUNT(CASE WHEN booking_ref IS NOT NULL THEN 1 END) as valid_booking_refs,
    MIN(booking_ref) as min_booking_ref,
    MAX(booking_ref) as max_booking_ref
FROM athina_booking_details;

-- ========================================
-- 4. 检查是否有重复记录
-- ========================================
SELECT 
    '重复记录检查' as check_type,
    booking_ref, 
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY created_at DESC) as record_ids
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- ========================================
-- 5. 检查booking_ref的数据分布
-- ========================================
SELECT 
    '数据分布' as check_type,
    booking_ref,
    client_name,
    corporate_name,
    created_at
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
ORDER BY booking_ref
LIMIT 10;

-- ========================================
-- 6. 测试约束功能
-- ========================================
-- 尝试插入重复的booking_ref（应该失败）
SET @test_ref = (SELECT MAX(booking_ref) + 1 FROM athina_booking_details WHERE booking_ref IS NOT NULL);

SELECT CONCAT('使用测试引用: ', COALESCE(@test_ref, 'NULL')) as test_info;

-- 插入测试记录
INSERT INTO athina_booking_details (header_id, booking_ref, client_name) 
VALUES (1, @test_ref, 'Test Client');

-- 尝试插入重复记录（应该失败）
INSERT INTO athina_booking_details (header_id, booking_ref, client_name) 
VALUES (1, @test_ref, 'Test Client Duplicate');

-- 清理测试数据
DELETE FROM athina_booking_details WHERE booking_ref = @test_ref;

-- ========================================
-- 7. 性能测试（可选）
-- ========================================
-- 测试整数查询性能
EXPLAIN SELECT * FROM athina_booking_details WHERE booking_ref = 12345;

-- 测试范围查询
EXPLAIN SELECT * FROM athina_booking_details WHERE booking_ref BETWEEN 10000 AND 20000;

-- ========================================
-- 8. 最终验证结果
-- ========================================
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM athina_booking_details WHERE booking_ref IS NOT NULL GROUP BY booking_ref HAVING COUNT(*) > 1) = 0 
        THEN '✅ 验证成功：booking_ref INT类型正常工作，无重复记录'
        ELSE '❌ 验证失败：仍有重复的booking_ref'
    END as final_result;
