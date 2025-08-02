-- 检查roles表结构
SELECT '=== roles表结构 ===' as info;
DESCRIBE roles;

-- 检查auth_users表结构
SELECT '=== auth_users表结构 ===' as info;
DESCRIBE auth_users;

-- 检查user_profiles表结构
SELECT '=== user_profiles表结构 ===' as info;
DESCRIBE user_profiles;

-- 检查roles表数据
SELECT '=== roles表数据 ===' as info;
SELECT * FROM roles ORDER BY id;

-- 检查auth_users表数据
SELECT '=== auth_users表数据 ===' as info;
SELECT * FROM auth_users ORDER BY id;

-- 检查user_profiles表数据
SELECT '=== user_profiles表数据 ===' as info;
SELECT * FROM user_profiles ORDER BY user_id;

-- 检查用户角色关联
SELECT '=== 用户角色关联 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id,
    r.name as role_name,
    r.description as role_description,
    u.is_active,
    u.is_verified
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;

-- 检查外键约束
SELECT '=== 外键约束 ===' as info;
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'travelindustry' 
AND TABLE_NAME IN ('auth_users', 'user_profiles')
AND REFERENCED_TABLE_NAME IS NOT NULL; 