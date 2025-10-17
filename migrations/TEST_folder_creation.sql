-- 测试文件夹创建功能
-- 这个脚本用于验证供应商文件夹创建功能

-- 1. 查看现有供应商信息
SELECT 
    supplier_id,
    name,
    country,
    city,
    CONCAT('E:\\MyProject\\MyTravelWork\\MyTravelPanel\\资源\\Supplier\\', 
           IFNULL(country, '未知国家'), '\\', 
           IFNULL(city, '未知城市'), '\\', 
           name) AS expected_folder_path
FROM suppliers 
WHERE name LIKE '%US-Bangla%' 
   OR name LIKE '%ACE TOURS%'
   OR name LIKE '%Singapore%'
LIMIT 10;

-- 2. 检查基础目录是否存在
-- 注意：这个查询无法直接检查文件系统，需要通过应用程序测试

-- 3. 建议的测试步骤：
-- a) 在供应商列表中搜索 "US-Bangla"
-- b) 点击该供应商的"文件夹"按钮
-- c) 系统应该自动创建文件夹：E:\MyProject\MyTravelWork\MyTravelPanel\资源\Supplier\新加坡\新加坡\US-Bangla Airlines Ltd
-- d) 验证文件夹是否成功创建并打开

-- 4. 测试其他供应商
SELECT 
    supplier_id,
    name,
    country,
    city
FROM suppliers 
WHERE country IS NULL 
   OR city IS NULL 
   OR name LIKE '%/%' 
   OR name LIKE '%<%' 
   OR name LIKE '%>%'
LIMIT 5;
