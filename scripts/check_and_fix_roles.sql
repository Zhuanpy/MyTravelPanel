-- 检查roles表状态
SELECT '=== 检查roles表结构 ===' as info;
DESCRIBE roles;

SELECT '=== 检查roles表数据 ===' as info;
SELECT * FROM roles;

-- 检查外键约束
SELECT '=== 检查外键约束 ===' as info;
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'travelindustry' 
AND TABLE_NAME = 'auth_users' 
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 重新创建roles数据（确保先清理）
SELECT '=== 清理并重新创建roles数据 ===' as info;
SET SQL_SAFE_UPDATES = 0;
DELETE FROM `user_profiles`;
DELETE FROM `auth_users`;
DELETE FROM `roles`;
SET SQL_SAFE_UPDATES = 1;

-- 重新插入roles数据
INSERT INTO `roles` (`id`, `name`, `description`, `permissions`) VALUES
(1, 'admin', '系统管理员，拥有所有权限', JSON_ARRAY(
    'manage_all_data',
    'manage_users',
    'manage_roles',
    'manage_orders',
    'publish_content',
    'view_analytics',
    'system_config'
)),
(2, 'staff', '公司员工，管理所属项目', JSON_ARRAY(
    'manage_own_projects',
    'create_quotes',
    'edit_quotes',
    'upload_files',
    'update_progress',
    'view_own_orders'
)),
(3, 'member', '会员客户，可以下单查看订单', JSON_ARRAY(
    'view_own_orders',
    'place_orders',
    'view_quotes',
    'view_invoices',
    'edit_profile'
)),
(4, 'guest', '普通访客，只能浏览公开信息', JSON_ARRAY(
    'view_public_info',
    'view_visa_services',
    'view_tour_packages'
));

-- 验证roles数据
SELECT '=== 验证roles数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id;

-- 现在创建测试用户
SELECT '=== 创建测试用户 ===' as info;
INSERT INTO `auth_users` (`username`, `email`, `password_hash`, `role_id`, `is_active`, `is_verified`) VALUES
('admin', 'admin@mytravelpanel.com', 'pbkdf2:sha256:600000$admin123$hash', 1, 1, 1),
('staff', 'staff@mytravelpanel.com', 'pbkdf2:sha256:600000$staff123$hash', 2, 1, 1),
('member', 'member@mytravelpanel.com', 'pbkdf2:sha256:600000$member123$hash', 3, 1, 1);

-- 创建用户资料
INSERT INTO `user_profiles` (`user_id`, `first_name`, `last_name`, `company`, `position`) VALUES
(1, '系统', '管理员', 'MyTravelPanel', '系统管理员'),
(2, '员工', '测试', 'MyTravelPanel', '员工'),
(3, '会员', '测试', '测试公司', '客户');

-- 最终验证
SELECT '=== 最终验证 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id,
    r.name as role_name,
    r.description as role_description
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id; 