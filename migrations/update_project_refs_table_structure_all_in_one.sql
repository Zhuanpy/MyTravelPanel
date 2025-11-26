-- =====================================================
-- 更新 project_refs 表结构（一次性执行版本）
-- 根据代码重构：删除冗余字段并重命名字段
-- 
-- ⚠️ 重要提示：
-- 1. 执行前请先备份数据库
-- 2. 建议在测试环境先验证
-- 3. 执行前确认没有应用正在使用这些字段
-- =====================================================

-- 开始事务（可选，根据MySQL版本）
-- START TRANSACTION;

-- =====================================================
-- 步骤1: 重命名字段
-- =====================================================

-- 1.1 先将 description 重命名为 detailed_description
ALTER TABLE `project_refs` 
CHANGE COLUMN `description` `detailed_description` VARCHAR(200) NOT NULL COMMENT '详细描述';

-- 1.2 将 name 重命名为 description  
ALTER TABLE `project_refs` 
CHANGE COLUMN `name` `description` VARCHAR(100) NULL COMMENT '描述';

-- =====================================================
-- 步骤2: 删除冗余字段
-- =====================================================

-- 2.1 删除供应商联系人字段（通过supplier_id关联获取）
ALTER TABLE `project_refs` 
DROP COLUMN `supplier_contact`,
DROP COLUMN `supplier_phone`;

-- 2.2 删除联系人信息字段（统一保存在HID表中）
ALTER TABLE `project_refs` 
DROP COLUMN `contact_name`,
DROP COLUMN `contact_phone`,
DROP COLUMN `contact_email`,
DROP COLUMN `leader_name`;

-- 2.3 删除交付日期字段
ALTER TABLE `project_refs` 
DROP COLUMN `expected_delivery_date`,
DROP COLUMN `actual_delivery_date`;

-- 提交事务（如果使用了事务）
-- COMMIT;

-- =====================================================
-- 验证：查看更新后的表结构
-- =====================================================
-- DESCRIBE `project_refs`;

-- =====================================================
-- 更新后的预期表结构：
-- =====================================================
-- id                          INT (PK, auto_increment)
-- header_id                   INT (FK)
-- ref_type_id                 INT (FK)
-- ref_number                  VARCHAR(30) (UNIQUE)
-- description                 VARCHAR(100) (原name字段)
-- detailed_description        VARCHAR(200) (原description字段)
-- status                      ENUM
-- created_at                  DATETIME
-- updated_at                  DATETIME
-- supplier_id                 INT (FK)
-- selling_price               DECIMAL(10,2)
-- cost_price                  DECIMAL(10,2)
-- currency                    VARCHAR(3)
-- remarks                     TEXT
-- attachments                 TEXT
-- payment_status              ENUM
-- extra_info                  TEXT
-- =====================================================

