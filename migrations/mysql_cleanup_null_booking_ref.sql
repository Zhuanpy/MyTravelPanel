-- MySQL清理NULL booking_ref记录脚本
-- 删除数据库中booking_ref为NULL的无效记录

-- ========================================
-- 1. 检查当前NULL booking_ref记录数量
-- ========================================
SELECT 
    '清理前统计' as info,
    COUNT(*) as total_records,
    COUNT(CASE WHEN booking_ref IS NULL THEN 1 END) as null_booking_refs,
    COUNT(CASE WHEN booking_ref IS NOT NULL THEN 1 END) as valid_booking_refs,
    COUNT(CASE WHEN is_subtotal = 1 THEN 1 END) as subtotal_records,
    COUNT(CASE WHEN is_subtotal = 0 THEN 1 END) as detail_records
FROM athina_booking_details;

-- ========================================
-- 2. 查看NULL booking_ref记录的详细信息
-- ========================================
SELECT 
    'NULL booking_ref记录' as info,
    id,
    header_id,
    booking_ref,
    client_name,
    corporate_name,
    is_subtotal,
    created_at
FROM athina_booking_details 
WHERE booking_ref IS NULL
ORDER BY created_at DESC
LIMIT 10;

-- ========================================
-- 3. 删除NULL booking_ref的普通记录（保留小计行）
-- ========================================
-- 只删除is_subtotal = 0 且 booking_ref IS NULL的记录
DELETE FROM athina_booking_details 
WHERE booking_ref IS NULL 
    AND is_subtotal = 0;

-- ========================================
-- 4. 可选：删除所有NULL booking_ref记录（包括小计行）
-- ========================================
-- 如果确定小计行也不需要，可以取消注释下面的语句
-- DELETE FROM athina_booking_details 
-- WHERE booking_ref IS NULL;

-- ========================================
-- 5. 清理后统计
-- ========================================
SELECT 
    '清理后统计' as info,
    COUNT(*) as total_records,
    COUNT(CASE WHEN booking_ref IS NULL THEN 1 END) as null_booking_refs,
    COUNT(CASE WHEN booking_ref IS NOT NULL THEN 1 END) as valid_booking_refs,
    COUNT(CASE WHEN is_subtotal = 1 THEN 1 END) as subtotal_records,
    COUNT(CASE WHEN is_subtotal = 0 THEN 1 END) as detail_records
FROM athina_booking_details;

-- ========================================
-- 6. 验证清理结果
-- ========================================
SELECT 
    '验证结果' as info,
    CASE 
        WHEN (SELECT COUNT(*) FROM athina_booking_details WHERE booking_ref IS NULL AND is_subtotal = 0) = 0 
        THEN '✅ 清理成功：没有NULL booking_ref的普通记录'
        ELSE '❌ 清理失败：仍有NULL booking_ref的普通记录'
    END as cleanup_result;

-- ========================================
-- 7. 检查数据完整性
-- ========================================
-- 检查是否有重复的booking_ref
SELECT 
    '重复检查' as info,
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 检查booking_ref的数据类型分布
SELECT 
    '数据类型检查' as info,
    MIN(booking_ref) as min_ref,
    MAX(booking_ref) as max_ref,
    AVG(booking_ref) as avg_ref,
    COUNT(DISTINCT booking_ref) as unique_refs
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL;
