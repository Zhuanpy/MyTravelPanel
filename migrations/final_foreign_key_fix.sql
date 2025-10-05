-- 最终的外键约束修复脚本
-- 使用完全不同的约束名称避免重复

-- 步骤1：查看现有外键约束
SHOW CREATE TABLE todos;
SHOW CREATE TABLE invitation_codes;
SHOW CREATE TABLE user_profiles;

-- 步骤2：删除现有外键约束（手动执行）
-- 请根据步骤1的结果，执行类似以下的命令：
-- ALTER TABLE todos DROP FOREIGN KEY constraint_name;
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name1;
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name2;
-- ALTER TABLE user_profiles DROP FOREIGN KEY constraint_name;

-- 步骤3：添加新的外键约束（使用全新的名称）

-- 修复 Todo 表的外键约束
ALTER TABLE todos 
ADD CONSTRAINT user_deletion_todos_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 修复 InvitationCode 表的外键约束
ALTER TABLE invitation_codes 
ADD CONSTRAINT user_deletion_invitation_created_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE CASCADE;

ALTER TABLE invitation_codes 
ADD CONSTRAINT user_deletion_invitation_used_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 确保 UserProfile 表的外键约束正确
ALTER TABLE user_profiles 
ADD CONSTRAINT user_deletion_profile_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

