-- MySQL Athina表约束修复 - 解决重复约束问题
-- 一键解决 Error Code: 1061

-- ========================================
-- 检查当前约束状态
-- ========================================
SELECT 
    '当前约束状态' as info,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME LIKE '%booking_ref%';

-- ========================================
-- 删除现有约束（如果存在）
-- ========================================
-- 方法1：删除约束
ALTER TABLE athina_booking_details 
DROP CONSTRAINT IF EXISTS uk_athina_booking_details_booking_ref;

-- 方法2：如果上面失败，尝试删除索引
DROP INDEX IF EXISTS uk_athina_booking_details_booking_ref ON athina_booking_details;

-- 方法3：如果上面都失败，查看具体的约束名称
-- 运行下面的查询查看实际的约束名称
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_TYPE = 'UNIQUE';

-- ========================================
-- 重新添加唯一约束
-- ========================================
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 验证约束是否添加成功
-- ========================================
SELECT 
    '约束添加结果' as info,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- ========================================
-- 最终检查：确保没有重复记录
-- ========================================
SELECT 
    '重复记录检查' as info,
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 如果上面查询有结果，说明还有重复记录，需要重新清理数据
-- 如果上面查询没有结果，说明约束添加成功
