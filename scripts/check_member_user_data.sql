-- 检查member用户的具体数据
SELECT '=== 检查member用户是否存在 ===' as info;
SELECT 
    id,
    username,
    email,
    password_hash,
    role_id,
    is_active,
    is_verified,
    created_at
FROM auth_users 
WHERE username = 'member' OR email = 'member@mytravelpanel.com';

SELECT '=== 检查所有用户数据 ===' as info;
SELECT 
    id,
    username,
    email,
    LEFT(password_hash, 50) as password_hash_preview,
    role_id,
    is_active,
    is_verified
FROM auth_users 
ORDER BY id;

SELECT '=== 检查roles表数据 ===' as info;
SELECT 
    id,
    name,
    description
FROM roles 
ORDER BY id;

SELECT '=== 检查用户角色关联 ===' as info;
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

-- 检查密码哈希格式
SELECT '=== 检查密码哈希格式 ===' as info;
SELECT 
    username,
    email,
    CASE 
        WHEN password_hash LIKE 'pbkdf2:sha256:%' THEN 'pbkdf2格式'
        WHEN password_hash LIKE 'sha256:%' THEN 'sha256格式'
        WHEN password_hash LIKE 'md5:%' THEN 'md5格式'
        WHEN password_hash IS NULL THEN 'NULL'
        ELSE '其他格式'
    END as hash_format,
    LENGTH(password_hash) as hash_length,
    LEFT(password_hash, 30) as hash_preview
FROM auth_users; 