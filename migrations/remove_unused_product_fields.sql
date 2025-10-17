-- ========================================
-- 移除 travelproducts 表中不需要的字段
-- 字段：duration_nights, contact_person, contact_phone, contact_email
-- ========================================

USE travel_panel_new;

-- ========================================
-- 步骤 1：备份数据（可选，建议）
-- ========================================

/*
-- 如果需要备份，可以先创建备份表
CREATE TABLE travelproducts_backup_20251017 AS
SELECT * FROM travelproducts;

SELECT '✅ 数据已备份到 travelproducts_backup_20251017' AS Status;
*/

-- ========================================
-- 步骤 2：检查要删除的字段是否有数据
-- ========================================

SELECT '检查字段数据...' AS Step;

SELECT 
    COUNT(*) AS total_products,
    COUNT(duration_nights) AS has_duration_nights,
    COUNT(contact_person) AS has_contact_person,
    COUNT(contact_phone) AS has_contact_phone,
    COUNT(contact_email) AS has_contact_email
FROM travelproducts;

-- 查看有这些数据的示例
SELECT 
    id, 
    product_name, 
    duration_nights, 
    contact_person, 
    contact_phone, 
    contact_email
FROM travelproducts
WHERE duration_nights IS NOT NULL 
   OR contact_person IS NOT NULL 
   OR contact_phone IS NOT NULL 
   OR contact_email IS NOT NULL
LIMIT 5;

-- ========================================
-- 步骤 3：删除字段
-- ========================================

SELECT '开始删除字段...' AS Step;

-- 删除 duration_nights 字段
ALTER TABLE travelproducts DROP COLUMN IF EXISTS duration_nights;
SELECT '✅ duration_nights 字段已删除' AS Status;

-- 删除 contact_person 字段
ALTER TABLE travelproducts DROP COLUMN IF EXISTS contact_person;
SELECT '✅ contact_person 字段已删除' AS Status;

-- 删除 contact_phone 字段
ALTER TABLE travelproducts DROP COLUMN IF EXISTS contact_phone;
SELECT '✅ contact_phone 字段已删除' AS Status;

-- 删除 contact_email 字段
ALTER TABLE travelproducts DROP COLUMN IF EXISTS contact_email;
SELECT '✅ contact_email 字段已删除' AS Status;

-- ========================================
-- 步骤 4：验证删除结果
-- ========================================

SELECT '验证删除结果...' AS Step;

-- 查看表结构
DESCRIBE travelproducts;

-- 统计剩余字段
SELECT 
    COUNT(*) AS total_columns
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'travel_panel_new'
  AND TABLE_NAME = 'travelproducts';

-- ========================================
-- 完成
-- ========================================

SELECT '✅ 字段删除完成！' AS Status;
SELECT '💡 联系信息现在应从 suppliers 表获取' AS Note;

