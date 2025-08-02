-- 检查会员用户登录问题
SELECT '=== 检查auth_users表中的会员用户 ===' as info;
SELECT 
    id,
    username,
    email,
    password_hash,
    role_id,
    is_active,
    is_verified
FROM auth_users 
WHERE username = 'member' OR email = 'member@mytravelpanel.com';

SELECT '=== 检查roles表中的member角色 ===' as info;
SELECT 
    id,
    name,
    description
FROM roles 
WHERE name = 'member';

SELECT '=== 检查所有用户和角色关联 ===' as info;
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

-- 检查密码哈希格式
SELECT '=== 检查密码哈希格式 ===' as info;
SELECT 
    username,
    email,
    CASE 
        WHEN password_hash LIKE 'pbkdf2:sha256:%' THEN 'pbkdf2格式'
        WHEN password_hash LIKE 'sha256:%' THEN 'sha256格式'
        WHEN password_hash LIKE 'md5:%' THEN 'md5格式'
        ELSE '其他格式'
    END as hash_format,
    LENGTH(password_hash) as hash_length
FROM auth_users; 