-- 修复用户删除时的外键约束问题
-- 为缺少 ondelete 约束的外键添加适当的删除行为

-- 修复用户删除时的外键约束问题
-- 为缺少 ondelete 约束的外键添加适当的删除行为

-- 注意：如果外键约束已存在，请先手动删除再执行此脚本
-- 可以使用以下命令查看现有外键约束：
-- SHOW CREATE TABLE table_name;

-- 1. 修复 Todo 表的外键约束
-- 删除用户时，删除相关的待办事项
-- 如果存在外键约束，请先删除：ALTER TABLE todos DROP FOREIGN KEY constraint_name;
ALTER TABLE todos 
ADD CONSTRAINT todos_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 2. 修复 InvitationCode 表的外键约束
-- 删除用户时，将创建者和使用者的ID设置为NULL（保留邀请码记录）
-- 如果存在外键约束，请先删除：ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name;
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_created_by_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL;

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_used_by_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 3. 确保 UserProfile 表的外键约束正确
-- 如果存在外键约束，请先删除：ALTER TABLE user_profiles DROP FOREIGN KEY constraint_name;
ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 4. 确保 EmailVerificationToken 表的外键约束正确
-- 如果存在外键约束，请先删除：ALTER TABLE email_verification_tokens DROP FOREIGN KEY constraint_name;
ALTER TABLE email_verification_tokens 
ADD CONSTRAINT email_verification_tokens_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;
