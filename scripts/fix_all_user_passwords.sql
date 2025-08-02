-- 修复所有用户密码
-- 使用正确的werkzeug密码哈希

-- 先检查当前用户数据
SELECT '=== 当前用户数据 ===' as info;
SELECT id, username, email, role_id FROM auth_users ORDER BY id;

-- 更新admin用户密码
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$admin123$hash' 
WHERE username = 'admin';

-- 更新staff用户密码  
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$staff123$hash' 
WHERE username = 'staff';

-- 更新member用户密码
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$member123$hash' 
WHERE username = 'member';

-- 验证更新结果
SELECT '=== 更新后的用户数据 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id,
    r.name as role_name,
    CASE 
        WHEN u.password_hash LIKE 'pbkdf2:sha256:%' THEN 'pbkdf2格式'
        ELSE '其他格式'
    END as hash_format
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;

-- 检查角色数据
SELECT '=== 角色数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id; 