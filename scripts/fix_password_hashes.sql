-- 修复密码哈希格式
-- 当前密码哈希格式不正确，需要更新为正确的werkzeug格式

-- 先检查当前密码哈希
SELECT '=== 当前密码哈希 ===' as info;
SELECT 
    username,
    email,
    password_hash,
    LENGTH(password_hash) as hash_length
FROM auth_users 
ORDER BY username;

-- 更新admin用户密码哈希
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$admin123$hash' 
WHERE username = 'admin';

-- 更新staff用户密码哈希
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$staff123$hash' 
WHERE username = 'staff';

-- 更新member用户密码哈希
UPDATE auth_users 
SET password_hash = 'pbkdf2:sha256:600000$member123$hash' 
WHERE username = 'member';

-- 验证更新结果
SELECT '=== 更新后的密码哈希 ===' as info;
SELECT 
    username,
    email,
    password_hash,
    LENGTH(password_hash) as hash_length,
    CASE 
        WHEN password_hash LIKE 'pbkdf2:sha256:%' THEN 'pbkdf2格式'
        ELSE '其他格式'
    END as hash_format
FROM auth_users 
ORDER BY username;

-- 注意：上面的哈希值只是示例，实际应该使用werkzeug生成的正确哈希
-- 请运行 generate_correct_passwords.py 脚本来获取正确的哈希值 