-- 完整的外键约束清理脚本
-- 清理所有重复和冲突的外键约束

-- 步骤1：清理 todos 表的重复外键约束
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS fk_todos_user_cascade;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS todos_ibfk_1;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS todos_user_id_cascade_fk;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS todos_user_id_fk;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS fk_todos_user_cascade;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS user_deletion_todos_fk;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS todos_user_fk_20241004_162336;
ALTER TABLE todos DROP FOREIGN KEY IF EXISTS todos_user_fk_abc123;

-- 步骤2：清理 invitation_codes 表的重复外键约束
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS fk_invitation_created_by_null;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS fk_invitation_created_by_cascade;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_codes_created_by_new_fk;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS fk_invitation_used_by_null;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_codes_used_by_new_fk;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS user_deletion_invitation_created_fk;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS user_deletion_invitation_used_fk;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_created_fk_20241004_162336;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_used_fk_20241004_162336;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_created_fk_def456;
ALTER TABLE invitation_codes DROP FOREIGN KEY IF EXISTS invitation_used_fk_ghi789;

-- 步骤3：清理 user_profiles 表的重复外键约束
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_profiles_user_id_fk;
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_profiles_user_id_cascade_fk;
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_profiles_user_id_new_fk;
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_deletion_profile_fk;
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_profiles_fk_20241004_162336;
ALTER TABLE user_profiles DROP FOREIGN KEY IF EXISTS user_profiles_fk_jkl012;

-- 步骤4：添加干净的外键约束
-- todos 表
ALTER TABLE todos 
ADD CONSTRAINT todos_user_final_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- invitation_codes 表
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_created_final_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE CASCADE;

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_used_final_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- user_profiles 表
ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_final_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;




