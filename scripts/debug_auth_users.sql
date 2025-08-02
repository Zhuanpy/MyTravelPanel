-- 检查auth_users表状态
SELECT '=== 检查auth_users表结构 ===' as info;
DESCRIBE auth_users;

SELECT '=== 检查auth_users表数据 ===' as info;
SELECT * FROM auth_users;

-- 检查user_profiles表状态
SELECT '=== 检查user_profiles表结构 ===' as info;
DESCRIBE user_profiles;

SELECT '=== 检查user_profiles表数据 ===' as info;
SELECT * FROM user_profiles;

-- 检查外键约束
SELECT '=== 检查user_profiles外键约束 ===' as info;
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'travelindustry' 
AND TABLE_NAME = 'user_profiles' 
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 检查roles表状态
SELECT '=== 检查roles表数据 ===' as info;
SELECT * FROM roles;

-- 重新创建所有数据（按正确顺序）
SELECT '=== 重新创建所有数据 ===' as info;

-- 1. 清理所有数据
SET SQL_SAFE_UPDATES = 0;
DELETE FROM user_profiles;
DELETE FROM auth_users;
DELETE FROM roles;
SET SQL_SAFE_UPDATES = 1;

-- 2. 重新创建roles
INSERT INTO roles (id, name, description, permissions) VALUES
(1, 'admin', '系统管理员，拥有所有权限', '["manage_all_data","manage_users","manage_roles","manage_orders","publish_content","view_analytics","system_config"]'),
(2, 'staff', '公司员工，管理所属项目', '["manage_own_projects","create_quotes","edit_quotes","upload_files","update_progress","view_own_orders"]'),
(3, 'member', '会员客户，可以下单查看订单', '["view_own_orders","place_orders","view_quotes","view_invoices","edit_profile"]'),
(4, 'guest', '普通访客，只能浏览公开信息', '["view_public_info","view_visa_services","view_tour_packages"]');

-- 3. 验证roles
SELECT '=== 验证roles数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id;

-- 4. 创建auth_users（明确指定id）
INSERT INTO auth_users (id, username, email, password_hash, role_id, is_active, is_verified) VALUES
(1, 'admin', 'admin@mytravelpanel.com', 'pbkdf2:sha256:600000$admin123$hash', 1, 1, 1),
(2, 'staff', 'staff@mytravelpanel.com', 'pbkdf2:sha256:600000$staff123$hash', 2, 1, 1),
(3, 'member', 'member@mytravelpanel.com', 'pbkdf2:sha256:600000$member123$hash', 3, 1, 1);

-- 5. 验证auth_users
SELECT '=== 验证auth_users数据 ===' as info;
SELECT id, username, email, role_id FROM auth_users ORDER BY id;

-- 6. 创建user_profiles
INSERT INTO user_profiles (user_id, first_name, last_name, company, position) VALUES
(1, '系统', '管理员', 'MyTravelPanel', '系统管理员'),
(2, '员工', '测试', 'MyTravelPanel', '员工'),
(3, '会员', '测试', '测试公司', '客户');

-- 7. 最终验证
SELECT '=== 最终验证 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id,
    r.name as role_name,
    p.first_name,
    p.last_name,
    p.company
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
LEFT JOIN user_profiles p ON u.id = p.user_id
ORDER BY u.id; 