-- MySQL Athina表booking_ref字段类型修改 - 简化版
-- 将booking_ref从varchar(100)改为int类型

-- ========================================
-- 1. 清理非数字数据
-- ========================================
-- 将非数字的booking_ref设置为NULL
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != ''
    AND booking_ref NOT REGEXP '^[0-9]+$';

-- ========================================
-- 2. 删除重复记录（保留最新的）
-- ========================================
DELETE d1 FROM athina_booking_details d1
INNER JOIN athina_booking_details d2 
WHERE d1.booking_ref = d2.booking_ref 
    AND d1.booking_ref IS NOT NULL
    AND d1.booking_ref REGEXP '^[0-9]+$'
    AND (
        d1.created_at < d2.created_at 
        OR (d1.created_at = d2.created_at AND d1.id < d2.id)
    );

-- ========================================
-- 3. 删除现有约束
-- ========================================
ALTER TABLE athina_booking_details 
DROP CONSTRAINT IF EXISTS uk_athina_booking_details_booking_ref;

-- ========================================
-- 4. 修改字段类型为INT
-- ========================================
ALTER TABLE athina_booking_details 
MODIFY COLUMN booking_ref INT NULL;

-- ========================================
-- 5. 重新添加唯一约束
-- ========================================
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 6. 验证结果
-- ========================================
-- 检查字段类型
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_KEY
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND COLUMN_NAME = 'booking_ref';

-- 检查约束
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

SELECT 'booking_ref字段类型修改完成！' as status;
