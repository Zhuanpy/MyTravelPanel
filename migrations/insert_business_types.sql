-- 插入默认业务类型数据
INSERT INTO business_types (name, code, description, is_active, sort_order, created_at, updated_at) VALUES
('机票', 'airline', '航空机票服务', 1, 10, NOW(), NOW()),
('景点/活动', 'attraction', '景点门票和活动预订', 1, 20, NOW(), NOW()),
('租车', 'car', '汽车租赁服务', 1, 30, NOW(), NOW()),
('邮轮', 'cruise', '邮轮旅游服务', 1, 40, NOW(), NOW()),
('渡轮', 'ferry', '渡轮运输服务', 1, 50, NOW(), NOW()),
('酒店', 'hotel', '酒店住宿服务', 1, 60, NOW(), NOW()),
('保险', 'insurance', '旅游保险服务', 1, 70, NOW(), NOW()),
('地接', 'land_tour', '当地旅游接待服务', 1, 80, NOW(), NOW()),
('其他', 'miscellaneous', '其他未分类服务', 1, 90, NOW(), NOW()),
('火车/大巴', 'rail_coach', '铁路和长途汽车服务', 1, 100, NOW(), NOW()),
('服务费', 'service_fee', '各类服务费用', 1, 110, NOW(), NOW()),
('门票', 'ticket', '各类景点门票', 1, 120, NOW(), NOW()),
('接送', 'transfer', '接送机和交通服务', 1, 130, NOW(), NOW()),
('签证', 'visa', '签证办理服务', 1, 140, NOW(), NOW()),
('代金券', 'voucher', '旅游代金券服务', 1, 150, NOW(), NOW()),
('旅游套餐', 'tour_package', '组合旅游产品套餐', 1, 160, NOW(), NOW()); 