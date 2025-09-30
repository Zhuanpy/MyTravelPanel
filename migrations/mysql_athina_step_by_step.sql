-- MySQL Athina表唯一约束迁移 - 分步执行版本
-- 请按顺序逐步执行，每步后检查结果

-- ========================================
-- 第1步：禁用安全更新模式
-- ========================================
SET SQL_SAFE_UPDATES = 0;

-- ========================================
-- 第2步：检查重复数据
-- ========================================
SELECT 
    booking_ref, 
    COUNT(*) as duplicate_count
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 如果上面查询有结果，继续第3步
-- 如果没有结果，直接跳到第5步

-- ========================================
-- 第3步：查看重复记录的详细信息
-- ========================================
SELECT 
    booking_ref,
    id,
    client_name,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY booking_ref ORDER BY created_at DESC, id DESC) as rn
FROM athina_booking_details 
WHERE booking_ref IN (
    SELECT booking_ref
    FROM athina_booking_details 
    WHERE booking_ref IS NOT NULL 
        AND booking_ref != '' 
        AND booking_ref != 'nan'
    GROUP BY booking_ref 
    HAVING COUNT(*) > 1
)
ORDER BY booking_ref, created_at DESC, id DESC;

-- ========================================
-- 第4步：删除重复记录（保留最新的）
-- ========================================
-- 先备份要删除的记录ID
CREATE TEMPORARY TABLE temp_delete_ids AS
SELECT id
FROM (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY booking_ref ORDER BY created_at DESC, id DESC) as rn
    FROM athina_booking_details 
    WHERE booking_ref IS NOT NULL 
        AND booking_ref != '' 
        AND booking_ref != 'nan'
) AS ranked
WHERE rn > 1;

-- 查看要删除的记录数量
SELECT COUNT(*) as records_to_delete FROM temp_delete_ids;

-- 执行删除
DELETE FROM athina_booking_details 
WHERE id IN (SELECT id FROM temp_delete_ids);

-- 清理临时表
DROP TEMPORARY TABLE temp_delete_ids;

-- 验证删除结果
SELECT 
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- ========================================
-- 第5步：清理无效的booking_ref
-- ========================================
-- 查看无效数据
SELECT 
    COUNT(*) as invalid_records
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- 清理无效数据
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- ========================================
-- 第6步：添加唯一约束
-- ========================================
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 第7步：验证约束
-- ========================================
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- ========================================
-- 第8步：恢复安全更新模式
-- ========================================
SET SQL_SAFE_UPDATES = 1;

-- ========================================
-- 第9步：最终验证
-- ========================================
SELECT 
    '迁移完成' as status,
    'athina_booking_details' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT booking_ref) as unique_booking_refs
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL;
