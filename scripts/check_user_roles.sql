-- 检查用户角色数据
SELECT '=== 检查roles表数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id;

SELECT '=== 检查auth_users表数据 ===' as info;
SELECT 
    id,
    username,
    email,
    role_id,
    is_active,
    is_verified
FROM auth_users ORDER BY id;

SELECT '=== 检查用户角色关联 ===' as info;
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

-- 检查是否有用户没有角色
SELECT '=== 检查无角色用户 ===' as info;
SELECT 
    u.id,
    u.username,
    u.email,
    u.role_id
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
WHERE r.id IS NULL;

-- 检查角色名称是否正确
SELECT '=== 检查角色名称 ===' as info;
SELECT DISTINCT r.name FROM roles r;

-- 测试登录逻辑
SELECT '=== 模拟登录逻辑 ===' as info;
SELECT 
    CASE 
        WHEN r.name = 'admin' THEN 'admin.dashboard'
        WHEN r.name = 'staff' THEN 'staff.dashboard'
        WHEN r.name = 'member' THEN 'member.dashboard'
        ELSE 'public.index'
    END as redirect_url,
    u.username,
    r.name as role_name
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id; 