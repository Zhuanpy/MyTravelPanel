-- 测试供应商文件夹路径构建
-- 这个脚本用于验证路径构建逻辑

-- 1. 查看现有供应商的国家和城市信息
SELECT 
    supplier_id,
    name,
    country,
    city,
    region,
    CONCAT('E:\\MyProject\\MyTravelWork\\MyTravelPanel\\资源\\旅游产品\\', 
           IFNULL(country, '未知国家'), '\\', 
           IFNULL(city, '未知城市'), '\\', 
           name) AS folder_path
FROM suppliers 
WHERE name LIKE '%ACE TOURS%' 
   OR name LIKE '%Singapore%'
   OR name LIKE '%新加坡%'
LIMIT 10;

-- 2. 更新一些示例供应商的城市信息（如果为空）
-- UPDATE suppliers SET city = '新加坡' WHERE name LIKE '%Singapore%' OR name LIKE '%新加坡%';
-- UPDATE suppliers SET city = '马来西亚' WHERE name LIKE '%Malaysia%' OR name LIKE '%马来西亚%';
-- UPDATE suppliers SET city = '泰国' WHERE name LIKE '%Thailand%' OR name LIKE '%泰国%';

-- 3. 查看所有供应商的路径构建结果
SELECT 
    supplier_id,
    name,
    country,
    city,
    CONCAT('E:\\MyProject\\MyTravelWork\\MyTravelPanel\\资源\\旅游产品\\', 
           IFNULL(country, '未知国家'), '\\', 
           IFNULL(city, '未知城市'), '\\', 
           name) AS expected_folder_path
FROM suppliers 
ORDER BY name
LIMIT 20;
