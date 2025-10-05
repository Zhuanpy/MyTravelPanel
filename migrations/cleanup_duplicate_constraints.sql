-- 清理重复的外键约束
-- 基于SHOW CREATE TABLE的结果

-- 清理 todos 表的重复外键约束
-- 删除所有现有的外键约束
ALTER TABLE todos DROP FOREIGN KEY fk_todos_user_cascade;
ALTER TABLE todos DROP FOREIGN KEY todos_ibfk_1;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_cascade_fk;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_fk;

-- 添加一个干净的外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_clean_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 现在请执行以下命令查看其他表的结构：
-- SHOW CREATE TABLE invitation_codes;
-- SHOW CREATE TABLE user_profiles;

-- 然后根据结果清理其他表的重复约束

