-- 检查roles表数据
SELECT '=== roles表数据 ===' as info;
SELECT id, name, description FROM roles ORDER BY id;

-- 验证用户角色关联
SELECT '=== 用户角色关联验证 ===' as info;
SELECT 
    u.username,
    u.role_id,
    r.name as role_name,
    r.description as role_description
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;

-- 测试登录重定向逻辑
SELECT '=== 登录重定向逻辑测试 ===' as info;
SELECT 
    u.username,
    r.name as role_name,
    CASE 
        WHEN r.name = 'admin' THEN 'admin.dashboard'
        WHEN r.name = 'staff' THEN 'staff.dashboard'
        WHEN r.name = 'member' THEN 'member.dashboard'
        ELSE 'public.index'
    END as expected_redirect_url
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;

-- 检查是否有角色名称不匹配的问题
SELECT '=== 角色名称检查 ===' as info;
SELECT 
    u.username,
    r.name as role_name,
    CASE 
        WHEN r.name = 'admin' THEN '✓ 正确'
        WHEN r.name = 'staff' THEN '✓ 正确'
        WHEN r.name = 'member' THEN '✓ 正确'
        WHEN r.name IS NULL THEN '✗ 无角色'
        ELSE CONCAT('✗ 未知角色: ', r.name)
    END as status
FROM auth_users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id; 