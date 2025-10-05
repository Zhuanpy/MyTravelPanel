-- 使用唯一名称的外键约束修复脚本
-- 基于时间戳的约束名称确保唯一性

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

-- 步骤3：添加新的外键约束（使用时间戳确保唯一性）

-- 修复 Todo 表的外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_fk_20241004_162336 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 修复 InvitationCode 表的外键约束
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_created_fk_20241004_162336 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE CASCADE;

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_used_fk_20241004_162336 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 确保 UserProfile 表的外键约束正确
ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_fk_20241004_162336 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

