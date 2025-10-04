-- 验证员工等级权限系统配置
-- 执行时间: 2025-10-04

-- 1. 验证字段配置
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    COLUMN_DEFAULT, 
    COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'user_profiles' 
AND COLUMN_NAME = 'staff_level';

-- 2. 验证索引配置
SHOW INDEX FROM user_profiles WHERE Column_name = 'staff_level';

-- 3. 查看当前所有员工的等级分布
SELECT 
    u.username,
    u.email,
    r.name as role_name,
    up.staff_level,
    CASE 
        WHEN up.staff_level = 1 THEN '普通员工'
        WHEN up.staff_level = 2 THEN '高级员工'
        ELSE '未设置'
    END as level_description
FROM auth_users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN roles r ON u.role_id = r.id
WHERE r.name = 'staff'
ORDER BY up.staff_level DESC, u.username;

-- 4. 统计各等级员工数量
SELECT 
    up.staff_level,
    COUNT(*) as count,
    CASE 
        WHEN up.staff_level = 1 THEN '普通员工'
        WHEN up.staff_level = 2 THEN '高级员工'
        ELSE '未设置'
    END as level_description
FROM auth_users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN roles r ON u.role_id = r.id
WHERE r.name = 'staff'
GROUP BY up.staff_level
ORDER BY up.staff_level;
