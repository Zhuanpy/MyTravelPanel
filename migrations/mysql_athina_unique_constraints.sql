-- MySQL数据库迁移脚本：为Athina表添加唯一约束
-- 执行时间：2025-01-27
-- 说明：
-- 1. athina_booking_headers.booking_header_id 已有唯一约束
-- 2. athina_booking_details.booking_ref 添加唯一约束
-- 3. 处理重复数据，保留最新记录

-- ========================================
-- 1. 检查并处理重复数据
-- ========================================

-- 查看athina_booking_details表中的重复booking_ref
SELECT 
    booking_ref, 
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY created_at DESC) as record_ids
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL 
    AND booking_ref != '' 
    AND booking_ref != 'nan'
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 删除重复的booking_ref记录，保留最新的记录（created_at最新的）
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

-- ========================================
-- 2. 清理无效的booking_ref数据
-- ========================================

-- 将无效的booking_ref设置为NULL（避免唯一约束冲突）
UPDATE athina_booking_details 
SET booking_ref = NULL 
WHERE booking_ref IS NOT NULL 
    AND (booking_ref = '' OR booking_ref = 'nan' OR TRIM(booking_ref) = '');

-- ========================================
-- 3. 添加唯一约束
-- ========================================

-- 为athina_booking_details.booking_ref添加唯一约束
-- 注意：如果约束已存在，此命令会报错，可以忽略
ALTER TABLE athina_booking_details 
ADD CONSTRAINT uk_athina_booking_details_booking_ref 
UNIQUE (booking_ref);

-- ========================================
-- 4. 验证约束和数据结构
-- ========================================

-- 查看athina_booking_headers表结构
DESCRIBE athina_booking_headers;

-- 查看athina_booking_details表结构
DESCRIBE athina_booking_details;

-- 查看athina_booking_details表的索引和约束
SHOW INDEX FROM athina_booking_details;

-- 查看表的创建语句
SHOW CREATE TABLE athina_booking_headers;
SHOW CREATE TABLE athina_booking_details;

-- ========================================
-- 5. 数据完整性检查
-- ========================================

-- 检查是否还有重复的booking_ref
SELECT 
    booking_ref, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_ref IS NOT NULL
GROUP BY booking_ref 
HAVING COUNT(*) > 1;

-- 检查booking_header_id的唯一性
SELECT 
    booking_header_id, 
    COUNT(*) as count 
FROM athina_booking_details 
WHERE booking_header_id IS NOT NULL
GROUP BY booking_header_id 
HAVING COUNT(*) > 1;

-- 统计各表的数据量
SELECT 'athina_booking_headers' as table_name, COUNT(*) as record_count FROM athina_booking_headers
UNION ALL
SELECT 'athina_booking_details' as table_name, COUNT(*) as record_count FROM athina_booking_details;

-- ========================================
-- 6. 可选：添加索引优化查询性能
-- ========================================

-- 为常用查询字段添加索引（如果不存在）
-- 注意：这些索引可能已经存在，如果存在会报错，可以忽略

-- booking_header_id索引（外键）
CREATE INDEX IF NOT EXISTS idx_athina_details_header_id ON athina_booking_details(header_id);

-- client_name索引（用于搜索）
CREATE INDEX IF NOT EXISTS idx_athina_details_client_name ON athina_booking_details(client_name);

-- corporate_name索引（用于搜索）
CREATE INDEX IF NOT EXISTS idx_athina_details_corporate_name ON athina_booking_details(corporate_name);

-- created_at索引（用于排序）
CREATE INDEX IF NOT EXISTS idx_athina_details_created_at ON athina_booking_details(created_at);

-- booking_date索引（用于时间范围查询）
CREATE INDEX IF NOT EXISTS idx_athina_details_book_date ON athina_booking_details(book_date);

-- dep_date索引（用于出发日期查询）
CREATE INDEX IF NOT EXISTS idx_athina_details_dep_date ON athina_booking_details(dep_date);

-- ========================================
-- 7. 回滚脚本（如果需要撤销更改）
-- ========================================

-- 如果需要撤销唯一约束，可以使用以下命令：
-- ALTER TABLE athina_booking_details DROP CONSTRAINT uk_athina_booking_details_booking_ref;

-- 如果需要撤销索引，可以使用以下命令：
-- DROP INDEX IF EXISTS idx_athina_details_header_id ON athina_booking_details;
-- DROP INDEX IF EXISTS idx_athina_details_client_name ON athina_booking_details;
-- DROP INDEX IF EXISTS idx_athina_details_corporate_name ON athina_booking_details;
-- DROP INDEX IF EXISTS idx_athina_details_created_at ON athina_booking_details;
-- DROP INDEX IF EXISTS idx_athina_details_book_date ON athina_booking_details;
-- DROP INDEX IF EXISTS idx_athina_details_dep_date ON athina_booking_details;
