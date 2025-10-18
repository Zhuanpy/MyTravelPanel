-- ========================================
-- 确保 company_info 表存在
-- 用于存储公司信息和Logo
-- ========================================

USE travelindustry;

-- 创建 company_info 表（如果不存在）
CREATE TABLE IF NOT EXISTS company_info (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    company_name VARCHAR(100) NOT NULL COMMENT '公司名称',
    company_description TEXT COMMENT '公司简介',
    phone VARCHAR(20) NOT NULL COMMENT '联系电话',
    email VARCHAR(100) NOT NULL COMMENT '电子邮箱',
    address TEXT NOT NULL COMMENT '公司地址',
    logo_path VARCHAR(200) COMMENT 'Logo图片路径（相对于App_new/static）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公司信息表';

-- 验证表结构
DESCRIBE company_info;

-- 显示当前公司信息
SELECT id, company_name, phone, email, logo_path 
FROM company_info 
ORDER BY id DESC 
LIMIT 1;

SELECT '✅ company_info 表准备完成！' AS Status;

