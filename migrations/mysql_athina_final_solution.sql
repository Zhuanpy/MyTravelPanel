-- MySQL Athina表唯一约束迁移 - 最终解决方案
-- 完全兼容MySQL安全更新模式

-- ========================================
-- 步骤1：禁用安全更新模式（必须）
-- ========================================
SET SQL_SAFE_UPDATES = 0;

-- ========================================
-- 步骤2：查看当前重复数据情况
-- ========================================
SELECT 
    '重复数据检查' as check_type,
    booking_ref, 
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY created_at DESC) as all_ids,
    GROUP_CONCAT(created_at ORDER BY created_at DESC) as all_dates
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- ========================================
-- 步骤3：删除重复记录（保留最新的）
-- ========================================
-- 使用更简单的方法：先标记要删除的记录，再删除
CREATE TEMPORARY TABLE temp_duplicate_ids AS
SELECT d1.id
FROM athina_booking_details d1
INNER JOIN athina_booking_details d2 
WHERE d1.booking_ref = d2.booking_ref 
    AND d1.booking_ref IS NOT NULL 
    AND d1.booking_ref != '' 
    AND d1.booking_ref != 'nan'
    AND (
        d1.created_at < d2.created_at 
        OR (d1.created_at = d2.created_at AND d1.id < d2.id)
    );

-- 查看将要删除的记录
SELECT '将要删除的记录' as info, COUNT(*) as count FROM temp_duplicate_ids;

-- 执行删除操作
DELETE FROM athina_booking_details 
WHERE id IN (SELECT id FROM temp_duplicate_ids);

-- 清理临时表
DROP TEMPORARY TABLE temp_duplicate_ids;

-- ========================================
-- 步骤4：清理无效的booking_ref
-- ========================================
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- ========================================
-- 步骤5：添加唯一约束
-- ========================================
-- 检查约束是否已存在
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- 添加唯一约束（如果不存在）
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 步骤6：验证结果
-- ========================================
-- 检查是否还有重复记录
SELECT 
    '重复记录检查' as check_type,
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 检查约束是否添加成功
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- 统计最终数据量
SELECT 
    'athina_booking_headers' as table_name, 
    COUNT(*) as record_count 
FROM athina_booking_headers
UNION ALL
SELECT 
    'athina_booking_details' as table_name, 
    COUNT(*) as record_count 
FROM athina_booking_details;

-- ========================================
-- 步骤7：恢复安全更新模式
-- ========================================
SET SQL_SAFE_UPDATES = 1;

-- ========================================
-- 完成提示
-- ========================================
SELECT 'Athina表唯一约束迁移完成！' as status;
