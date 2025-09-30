-- MySQL Athina表唯一约束检查和处理
-- 解决 Error Code: 1061 重复约束名称问题

-- ========================================
-- 步骤1：检查现有约束
-- ========================================
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME LIKE '%booking_ref%';

-- ========================================
-- 步骤2：检查约束是否已存在
-- ========================================
SELECT 
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';

-- ========================================
-- 步骤3：如果约束已存在，先删除再重新添加
-- ========================================
-- 删除现有约束（如果存在）
ALTER TABLE athina_booking_details 
DROP CONSTRAINT IF EXISTS uk_athina_booking_details_booking_ref;

-- 或者使用这种方式删除索引（MySQL 5.7+）
DROP INDEX IF EXISTS uk_athina_booking_details_booking_ref ON athina_booking_details;

-- ========================================
-- 步骤4：重新添加唯一约束
-- ========================================
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 步骤5：验证约束是否添加成功
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
-- 步骤6：测试约束是否工作
-- ========================================
-- 尝试插入重复数据来测试约束
-- 这应该会失败，证明约束工作正常
INSERT INTO athina_booking_details (header_id, booking_ref, client_name) 
VALUES (1, 'TEST_DUPLICATE', 'Test Client');

-- 如果上面的插入成功，说明约束没有工作
-- 如果失败，说明约束正常工作

-- 清理测试数据
DELETE FROM athina_booking_details WHERE booking_ref = 'TEST_DUPLICATE';

-- ========================================
-- 最终验证
-- ========================================
SELECT 
    '约束添加完成' as status,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'athina_booking_details'
    AND CONSTRAINT_NAME = 'uk_athina_booking_details_booking_ref';
