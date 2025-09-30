-- MySQL Athina表唯一约束迁移 - 核心操作
-- 执行前请备份数据库！

-- 1. 删除重复的booking_ref记录（保留最新的）
DELETE d1 FROM athina_booking_details d1
INNER JOIN athina_booking_details d2 
WHERE d1.booking_ref = d2.booking_ref 
    AND d1.booking_ref IS NOT NULL 
    AND d1.booking_ref != '' 
    AND d1.booking_ref != 'nan'
    AND (
        d1.created_at < d2.created_at 
        OR (d1.created_at = d2.created_at AND d1.id < d2.id)
    );

-- 2. 清理无效的booking_ref
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- 3. 添加唯一约束
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- 4. 验证结果
SELECT 
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;
