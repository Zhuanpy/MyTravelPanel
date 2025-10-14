-- 修复用户删除问题的简化脚本
-- 只处理现有的表，不创建新表

-- 步骤1：查看现有外键约束
SHOW CREATE TABLE todos;
SHOW CREATE TABLE invitation_codes;
SHOW CREATE TABLE user_profiles;

-- 步骤2：手动删除现有外键约束
-- 请根据上面的结果，执行类似以下的命令（将 constraint_name 替换为实际名称）：
-- ALTER TABLE todos DROP FOREIGN KEY constraint_name;
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name1;
-- ALTER TABLE invitation_codes DROP FOREIGN KEY constraint_name2;
-- ALTER TABLE user_profiles DROP FOREIGN KEY constraint_name;

-- 步骤3：添加新的外键约束（执行下面的命令）

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








