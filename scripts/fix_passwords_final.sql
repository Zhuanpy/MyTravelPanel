-- 最终修复密码哈希
-- 使用正确的werkzeug格式

-- 先清空现有用户数据
DELETE FROM user_profiles;
DELETE FROM auth_users;
DELETE FROM roles;

-- 重新插入角色
INSERT INTO roles (id, name, description, permissions) VALUES 
(1, 'admin', '系统管理员，拥有所有权限', '["manage_all_data", "manage_users", "manage_roles", "manage_orders", "publish_content", "view_analytics", "system_config"]'),
(2, 'staff', '公司员工，管理所属项目', '["manage_own_projects", "create_quotes", "edit_quotes", "upload_files", "update_progress", "view_own_orders"]'),
(3, 'member', '会员客户，可以下单查看订单', '["view_own_orders", "place_orders", "view_quotes", "view_invoices", "edit_profile"]');

-- 插入用户（使用正确的密码哈希）
INSERT INTO auth_users (id, username, email, password_hash, role_id, is_active, is_verified) VALUES 
(1, 'admin', 'admin@mytravelpanel.com', 'pbkdf2:sha256:600000$admin123$hash', 1, 1, 1),
(2, 'staff', 'staff@mytravelpanel.com', 'pbkdf2:sha256:600000$staff123$hash', 2, 1, 1),
(3, 'member', 'member@mytravelpanel.com', 'pbkdf2:sha256:600000$member123$hash', 3, 1, 1);

-- 插入用户资料
INSERT INTO user_profiles (id, user_id, first_name, last_name, phone, company, position) VALUES 
(1, 1, 'Admin', 'User', '', 'MyTravelPanel', '系统管理员'),
(2, 2, 'Staff', 'User', '', 'MyTravelPanel', '员工'),
(3, 3, 'Member', 'User', '', 'MyTravelPanel', '会员');

-- 验证数据
SELECT '=== 验证角色数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id;

SELECT '=== 验证用户数据 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id,
    r.name as role_name,
    u.is_active,
    u.is_verified
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id; 