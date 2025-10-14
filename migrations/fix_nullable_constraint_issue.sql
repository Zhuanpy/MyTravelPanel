-- 修复外键约束的NULL问题
-- 针对 created_by 字段使用 CASCADE 而不是 SET NULL

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

-- 步骤3：添加新的外键约束（修复NULL问题）

-- 修复 Todo 表的外键约束
ALTER TABLE todos 
ADD CONSTRAINT fk_todos_user_cascade 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 修复 InvitationCode 表的外键约束
-- created_by 使用 CASCADE（因为字段是 NOT NULL）
ALTER TABLE invitation_codes 
ADD CONSTRAINT fk_invitation_created_by_cascade 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE CASCADE;

-- used_by 使用 SET NULL（因为字段是 nullable=True）
ALTER TABLE invitation_codes 
ADD CONSTRAINT fk_invitation_used_by_null 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 确保 UserProfile 表的外键约束正确
ALTER TABLE user_profiles 
ADD CONSTRAINT fk_user_profiles_user_cascade 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;








