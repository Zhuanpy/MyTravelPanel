-- 手动修复外键约束的步骤
-- 请按顺序执行以下命令

-- 步骤1：查看现有外键约束
-- 执行以下命令查看每个表的外键约束：
SHOW CREATE TABLE todos;
SHOW CREATE TABLE invitation_codes;
SHOW CREATE TABLE user_profiles;
SHOW CREATE TABLE email_verification_tokens;

-- 步骤2：删除现有外键约束（如果存在）
-- 请根据步骤1的结果，将下面的 constraint_name 替换为实际的外键约束名称

-- 删除 todos 表的外键约束（如果有的话）
-- ALTER TABLE todos DROP FOREIGN KEY constraint_name;

-- 删除 invitation_codes 表的外键约束（如果有的话）
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name1;
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name2;

-- 删除 user_profiles 表的外键约束（如果有的话）
-- ALTER TABLE user_profiles DROP FOREIGN KEY constraint_name;

-- 删除 email_verification_tokens 表的外键约束（如果有的话）
-- ALTER TABLE email_verification_tokens DROP FOREIGN KEY constraint_name;

-- 步骤3：添加新的外键约束
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

-- 确保 EmailVerificationToken 表的外键约束正确（如果表存在）
ALTER TABLE email_verification_tokens 
ADD CONSTRAINT email_verification_tokens_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;




