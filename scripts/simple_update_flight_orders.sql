-- 简化版：更新flight_orders表中的项目关联数据
-- 请根据实际情况选择执行相应的部分

-- ==========================================
-- 第一步：查看现有数据情况
-- ==========================================
SELECT 
    '数据统计' as info,
    COUNT(*) as total_orders,
    COUNT(project_header_id) as orders_with_header,
    COUNT(project_ref_id) as orders_with_ref,
    COUNT(CASE WHEN project_header_id IS NULL AND project_ref_id IS NULL THEN 1 END) as orders_without_project
FROM flight_orders;

-- ==========================================
-- 第二步：查看现有项目数据
-- ==========================================
SELECT 'Project Headers' as table_name, COUNT(*) as count FROM project_headers
UNION ALL
SELECT 'Project Refs' as table_name, COUNT(*) as count FROM project_refs;

-- ==========================================
-- 第三步：选择更新策略
-- ==========================================

-- 策略A：如果hid_number与HID编号格式匹配，直接关联
-- 执行前请确认hid_number的格式是否与HID编号格式一致
/*
UPDATE flight_orders fo
LEFT JOIN project_headers ph ON fo.hid_number = ph.hid
SET fo.project_header_id = ph.id
WHERE fo.project_header_id IS NULL 
  AND fo.hid_number IS NOT NULL 
  AND ph.id IS NOT NULL;
*/

-- 策略B：为每个订单创建独立的项目（推荐）
-- 1. 创建项目主表记录
INSERT INTO project_headers (hid, desc, company_name, staff_name, status, created_at, updated_at)
SELECT 
    CONCAT('H', DATE_FORMAT(fo.created_date, '%Y%m%d'), LPAD(fo.id, 3, '0')) as hid,
    CONCAT('机票订单项目 - ', fo.order_number) as desc,
    COALESCE(fo.contact_person, '默认客户') as company_name,
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

-- 2. 更新flight_orders表，关联到新创建的项目
UPDATE flight_orders fo
JOIN project_headers ph ON ph.hid = CONCAT('H', DATE_FORMAT(fo.created_date, '%Y%m%d'), LPAD(fo.id, 3, '0'))
SET fo.project_header_id = ph.id
WHERE fo.project_header_id IS NULL;

-- 3. 为每个项目创建默认REF
-- 首先获取机票业务类型的ID
SET @airline_type_id = (SELECT id FROM business_types WHERE code = 'airline' LIMIT 1);

-- 如果没有找到机票类型，使用ID 1作为默认值
SET @airline_type_id = COALESCE(@airline_type_id, 1);

INSERT INTO project_refs (header_id, ref_number, name, ref_type_id, description, supplier_id, currency, status, payment_status, created_at, updated_at)
SELECT 
    ph.id as header_id,
    CONCAT(ph.hid, '-R01') as ref_number,
    CONCAT('机票订单 - ', fo.order_number) as name,
    @airline_type_id as ref_type_id,
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

-- 4. 更新flight_orders表，关联到新创建的REF
UPDATE flight_orders fo
JOIN project_refs pr ON pr.header_id = fo.project_header_id
SET fo.project_ref_id = pr.id
WHERE fo.project_ref_id IS NULL;

-- ==========================================
-- 第四步：验证更新结果
-- ==========================================
SELECT 
    '更新后统计' as info,
    COUNT(*) as total_orders,
    COUNT(project_header_id) as orders_with_header,
    COUNT(project_ref_id) as orders_with_ref,
    COUNT(CASE WHEN project_header_id IS NULL AND project_ref_id IS NULL THEN 1 END) as orders_without_project
FROM flight_orders;

-- 查看更新后的示例数据
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
ORDER BY fo.id DESC
LIMIT 10; 