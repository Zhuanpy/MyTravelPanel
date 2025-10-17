-- 添加 city 字段到 suppliers 表
-- 执行前请备份数据库

-- 1. 添加 city 字段
ALTER TABLE suppliers ADD COLUMN city VARCHAR(50) NULL COMMENT '城市' AFTER country;

-- 2. 更新现有数据（可选）
-- 根据供应商名称或其他信息推断城市
-- 这里可以根据实际情况更新

-- 示例：更新一些已知城市的供应商
-- UPDATE suppliers SET city = '新加坡' WHERE name LIKE '%新加坡%' OR name LIKE '%Singapore%';
-- UPDATE suppliers SET city = '马来西亚' WHERE name LIKE '%马来西亚%' OR name LIKE '%Malaysia%';
-- UPDATE suppliers SET city = '泰国' WHERE name LIKE '%泰国%' OR name LIKE '%Thailand%';

-- 3. 验证结果
SELECT supplier_id, name, country, city, region FROM suppliers LIMIT 10;
