-- 完整的外键约束修复脚本
-- 包括创建缺失的表和修复外键约束

-- 步骤1：创建缺失的表（如果不存在）

-- 创建 email_verification_tokens 表
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_user_id (user_id),
    INDEX idx_email (email),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮箱验证令牌表';

-- 创建 email_verification_codes 表（用于两步验证注册）
CREATE TABLE IF NOT EXISTS email_verification_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_verification_code (verification_code),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_used (is_used)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮箱验证码表';

-- 步骤2：查看现有外键约束（用于调试）
-- 取消注释以下行来查看现有约束：
-- SHOW CREATE TABLE todos;
-- SHOW CREATE TABLE invitation_codes;
-- SHOW CREATE TABLE user_profiles;

-- 步骤3：删除现有外键约束（手动执行）
-- 请根据 SHOW CREATE TABLE 的结果，手动删除现有的外键约束
-- 例如：
-- ALTER TABLE todos DROP FOREIGN KEY constraint_name;

-- 步骤4：添加新的外键约束

-- 修复 Todo 表的外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 修复 InvitationCode 表的外键约束
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_created_by_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL;

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_used_by_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 确保 UserProfile 表的外键约束正确
ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 为 email_verification_tokens 表添加外键约束
ALTER TABLE email_verification_tokens 
ADD CONSTRAINT email_verification_tokens_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

