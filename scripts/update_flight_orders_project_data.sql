-- 更新flight_orders表中的项目关联数据
-- 执行前请备份数据库

-- 1. 查看现有数据情况
SELECT 
    COUNT(*) as total_orders,
    COUNT(project_header_id) as orders_with_header,
    COUNT(project_ref_id) as orders_with_ref,
    COUNT(CASE WHEN project_header_id IS NULL AND project_ref_id IS NULL THEN 1 END) as orders_without_project
FROM flight_orders;

-- 2. 查看现有的HID和REF数据
SELECT 'Project Headers' as table_name, COUNT(*) as count FROM project_headers
UNION ALL
SELECT 'Project Refs' as table_name, COUNT(*) as count FROM project_refs;

-- 3. 查看一些示例数据
SELECT 
    fo.id,
    fo.order_number,
    fo.hid_number,
    fo.passenger_name,
    fo.project_header_id,
    fo.project_ref_id,
    ph.hid as header_hid,
    pr.ref_number as ref_number
FROM flight_orders fo
LEFT JOIN project_headers ph ON fo.project_header_id = ph.id
LEFT JOIN project_refs pr ON fo.project_ref_id = pr.id
LIMIT 10;

-- 4. 基于hid_number匹配项目主表（如果hid_number格式与HID编号格式相似）
-- 注意：这里需要根据实际的hid_number格式调整匹配逻辑
UPDATE flight_orders fo
LEFT JOIN project_headers ph ON fo.hid_number = ph.hid
SET fo.project_header_id = ph.id
WHERE fo.project_header_id IS NULL 
  AND fo.hid_number IS NOT NULL 
  AND ph.id IS NOT NULL;

-- 5. 为没有关联的订单创建默认项目（可选）
-- 如果你希望为所有没有关联的订单创建一个默认项目，可以执行以下步骤：

-- 5.1 创建默认项目主表记录
INSERT INTO project_headers (hid, desc, company_name, staff_name, status, created_at, updated_at)
SELECT 
    CONCAT('H', DATE_FORMAT(fo.created_date, '%Y%m%d'), LPAD(fo.id, 3, '0')) as hid,
    CONCAT('机票订单项目 - ', fo.order_number) as desc,
    '默认客户' as company_name,
    '系统管理员' as staff_name,
    'active' as status,
    NOW() as created_at,
    NOW() as updated_at
FROM flight_orders fo
WHERE fo.project_header_id IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM project_headers ph 
    WHERE ph.hid = CONCAT('H', DATE_FORMAT(fo.created_date, '%Y%m%d'), LPAD(fo.id, 3, '0'))
  );

-- 5.2 更新flight_orders表，关联到新创建的项目
UPDATE flight_orders fo
JOIN project_headers ph ON ph.hid = CONCAT('H', DATE_FORMAT(fo.created_date, '%Y%m%d'), LPAD(fo.id, 3, '0'))
SET fo.project_header_id = ph.id
WHERE fo.project_header_id IS NULL;

-- 5.3 为每个项目创建默认REF
INSERT INTO project_refs (header_id, ref_number, name, ref_type_id, description, supplier_id, currency, status, payment_status, created_at, updated_at)
SELECT 
    ph.id as header_id,
    CONCAT(ph.hid, '-R01') as ref_number,
    CONCAT('机票订单 - ', fo.order_number) as name,
    1 as ref_type_id, -- 假设1是机票类型，请根据实际情况调整
    CONCAT('机票订单：', fo.order_number, ' - ', fo.passenger_name) as description,
    NULL as supplier_id,
    'SGD' as currency,
    'completed' as status,
    'paid' as payment_status,
    NOW() as created_at,
    NOW() as updated_at
FROM project_headers ph
JOIN flight_orders fo ON fo.project_header_id = ph.id
WHERE NOT EXISTS (
    SELECT 1 FROM project_refs pr WHERE pr.header_id = ph.id
);

-- 5.4 更新flight_orders表，关联到新创建的REF
UPDATE flight_orders fo
JOIN project_refs pr ON pr.header_id = fo.project_header_id
SET fo.project_ref_id = pr.id
WHERE fo.project_ref_id IS NULL;

-- 6. 验证更新结果
SELECT 
    COUNT(*) as total_orders,
    COUNT(project_header_id) as orders_with_header,
    COUNT(project_ref_id) as orders_with_ref,
    COUNT(CASE WHEN project_header_id IS NULL AND project_ref_id IS NULL THEN 1 END) as orders_without_project
FROM flight_orders;

-- 7. 查看更新后的示例数据
SELECT 
    fo.id,
    fo.order_number,
    fo.hid_number,
    fo.passenger_name,
    fo.project_header_id,
    fo.project_ref_id,
    ph.hid as header_hid,
    pr.ref_number as ref_number
FROM flight_orders fo
LEFT JOIN project_headers ph ON fo.project_header_id = ph.id
LEFT JOIN project_refs pr ON fo.project_ref_id = pr.id
LIMIT 10; 