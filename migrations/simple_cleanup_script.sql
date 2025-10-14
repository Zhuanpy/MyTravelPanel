-- 简单的外键约束清理脚本
-- 只删除已知存在的约束

-- 步骤1：删除 todos 表中已知存在的约束
-- 根据 SHOW CREATE TABLE 的结果，我们知道这些约束存在：
ALTER TABLE todos DROP FOREIGN KEY fk_todos_user_cascade;
ALTER TABLE todos DROP FOREIGN KEY todos_ibfk_1;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_cascade_fk;
ALTER TABLE todos DROP FOREIGN KEY todos_user_id_fk;

-- 步骤2：添加干净的 todos 外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_simple_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 步骤3：现在请执行以下命令查看其他表的结构：
SHOW CREATE TABLE invitation_codes;
SHOW CREATE TABLE user_profiles;

-- 然后根据结果手动删除其他表的重复约束








