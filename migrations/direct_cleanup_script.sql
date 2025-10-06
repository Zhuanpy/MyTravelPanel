-- 直接清理脚本
-- 基于已知的约束信息

-- 清理 todos 表的重复约束
ALTER TABLE todos DROP FOREIGN KEY fk_todos_user_cascade;
ALTER TABLE todos DROP FOREIGN KEY todos_ibfk_1;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_cascade_fk;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_fk;

-- 添加干净的 todos 约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_direct_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 现在请查看其他表的结构并手动处理：
-- SHOW CREATE TABLE invitation_codes;
-- SHOW CREATE TABLE user_profiles;


