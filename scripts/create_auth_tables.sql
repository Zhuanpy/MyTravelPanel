-- 认证系统数据库表创建脚本
-- 用于创建认证相关的数据库表和初始化基础数据

USE travelindustry;

-- 1. 创建角色表
CREATE TABLE IF NOT EXISTS `roles` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(50) NOT NULL COMMENT '角色名称',
    `description` varchar(200) DEFAULT NULL COMMENT '角色描述',
    `permissions` json DEFAULT NULL COMMENT '权限列表',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_role_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 2. 创建认证用户表
CREATE TABLE IF NOT EXISTS `auth_users` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `username` varchar(80) NOT NULL COMMENT '用户名',
    `email` varchar(120) NOT NULL COMMENT '邮箱',
    `password_hash` varchar(255) NOT NULL COMMENT '密码哈希',
    `role_id` int(11) NOT NULL COMMENT '角色ID',
    `is_active` tinyint(1) DEFAULT 1 COMMENT '是否激活',
    `is_verified` tinyint(1) DEFAULT 0 COMMENT '是否验证',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `last_login` datetime DEFAULT NULL COMMENT '最后登录时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_role_id` (`role_id`),
    CONSTRAINT `fk_auth_users_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='认证用户表';

-- 3. 创建用户资料表
CREATE TABLE IF NOT EXISTS `user_profiles` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `user_id` int(11) NOT NULL COMMENT '用户ID',
    `first_name` varchar(50) DEFAULT NULL COMMENT '名',
    `last_name` varchar(50) DEFAULT NULL COMMENT '姓',
    `phone` varchar(20) DEFAULT NULL COMMENT '电话',
    `company` varchar(100) DEFAULT NULL COMMENT '公司',
    `position` varchar(50) DEFAULT NULL COMMENT '职位',
    `avatar` varchar(255) DEFAULT NULL COMMENT '头像路径',
    `preferences` json DEFAULT NULL COMMENT '用户偏好',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`),
    CONSTRAINT `fk_user_profiles_user` FOREIGN KEY (`user_id`) REFERENCES `auth_users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户资料表';

-- 4. 初始化角色数据
INSERT INTO `roles` (`name`, `description`, `permissions`) VALUES
('admin', '系统管理员，拥有所有权限', JSON_ARRAY(
    'manage_all_data',
    'manage_users',
    'manage_roles',
    'manage_orders',
    'publish_content',
    'view_analytics',
    'system_config'
)),
('staff', '公司员工，管理所属项目', JSON_ARRAY(
    'manage_own_projects',
    'create_quotes',
    'edit_quotes',
    'upload_files',
    'update_progress',
    'view_own_orders'
)),
('member', '会员客户，可以下单查看订单', JSON_ARRAY(
    'view_own_orders',
    'place_orders',
    'view_quotes',
    'view_invoices',
    'edit_profile'
)),
('guest', '普通访客，只能浏览公开信息', JSON_ARRAY(
    'view_public_info',
    'view_visa_services',
    'view_tour_packages'
))
ON DUPLICATE KEY UPDATE
    `description` = VALUES(`description`),
    `permissions` = VALUES(`permissions`),
    `updated_at` = CURRENT_TIMESTAMP;

-- 5. 创建默认管理员账户（可选）
-- 注意：这里只是创建角色，实际用户创建需要通过应用进行
-- 默认管理员信息：
-- 用户名: admin
-- 邮箱: admin@mytravelpanel.com
-- 密码: admin123 (需要在应用中设置)

-- 6. 验证数据
SELECT 
    'Roles' as table_name,
    COUNT(*) as record_count
FROM roles
UNION ALL
SELECT 
    'Auth Users' as table_name,
    COUNT(*) as record_count
FROM auth_users
UNION ALL
SELECT 
    'User Profiles' as table_name,
    COUNT(*) as record_count
FROM user_profiles;

-- 7. 显示角色信息
SELECT 
    r.name as role_name,
    r.description,
    JSON_LENGTH(r.permissions) as permission_count
FROM roles r
ORDER BY r.id; 