-- MySQL Athina表唯一约束迁移 - 安全模式兼容版本
-- 解决 Error Code: 1175 安全更新模式问题

-- 方法1：临时禁用安全更新模式（推荐）
SET SQL_SAFE_UPDATES = 0;

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

-- 恢复安全更新模式
SET SQL_SAFE_UPDATES = 1;

-- 验证结果
SELECT 
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 如果上面的方法仍然有问题，使用下面的替代方案：

-- ========================================
-- 替代方案：使用临时表方法
-- ========================================

-- 创建临时表存储要保留的记录ID
CREATE TEMPORARY TABLE temp_keep_records AS
SELECT MAX(id) as keep_id
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
GROUP BY booking_ref;

-- 删除不在保留列表中的重复记录
DELETE FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
    AND id NOT IN (SELECT keep_id FROM temp_keep_records);

-- 清理临时表
DROP TEMPORARY TABLE temp_keep_records;

-- 清理无效的booking_ref
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- 添加唯一约束
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);
