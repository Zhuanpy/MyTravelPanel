-- MySQL Athina表唯一约束迁移 - 最简单解决方案
-- 使用主键删除，兼容安全更新模式

-- 1. 查找重复的booking_ref记录
SELECT 
    booking_ref, 
    id,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY booking_ref ORDER BY created_at DESC, id DESC) as rn
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
ORDER BY booking_ref, created_at DESC;

-- 2. 删除重复记录（保留每组中created_at最新且id最大的记录）
DELETE FROM athina_booking_details 
WHERE id IN (
    SELECT id FROM (
        SELECT 
            id,
            ROW_NUMBER() OVER (PARTITION BY booking_ref ORDER BY created_at DESC, id DESC) as rn
        FROM athina_booking_details 
        WHERE booking_ref IS NOT NULL 
            AND booking_ref != '' 
            AND booking_ref != 'nan'
    ) AS temp 
    WHERE rn > 1
);

-- 3. 清理无效的booking_ref
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- 4. 添加唯一约束
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- 5. 验证结果
SELECT 
    '重复记录检查' as check_type,
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1

UNION ALL

SELECT 
    '总记录数' as check_type,
    'athina_booking_details' as booking_ref,
    COUNT(*) as count
FROM athina_booking_details;
