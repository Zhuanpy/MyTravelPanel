-- 智能外键约束清理脚本
-- 自动检测并删除存在的约束

-- 清理 todos 表的外键约束
SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                       WHERE TABLE_SCHEMA = DATABASE() 
                       AND TABLE_NAME = 'todos' 
                       AND COLUMN_NAME = 'user_id' 
                       AND REFERENCED_TABLE_NAME = 'auth_users' 
                       LIMIT 1);

SET @sql = IF(@constraint_name IS NOT NULL, 
              CONCAT('ALTER TABLE todos DROP FOREIGN KEY ', @constraint_name), 
              'SELECT "No foreign key constraint found for todos.user_id"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 清理指向旧 users 表的约束
SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                       WHERE TABLE_SCHEMA = DATABASE() 
                       AND TABLE_NAME = 'todos' 
                       AND COLUMN_NAME = 'user_id' 
                       AND REFERENCED_TABLE_NAME = 'users' 
                       LIMIT 1);

SET @sql = IF(@constraint_name IS NOT NULL, 
              CONCAT('ALTER TABLE todos DROP FOREIGN KEY ', @constraint_name), 
              'SELECT "No foreign key constraint found for todos.user_id -> users"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加干净的 todos 外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_smart_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 清理 invitation_codes 表的 created_by 约束
SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                       WHERE TABLE_SCHEMA = DATABASE() 
                       AND TABLE_NAME = 'invitation_codes' 
                       AND COLUMN_NAME = 'created_by' 
                       AND REFERENCED_TABLE_NAME = 'auth_users' 
                       LIMIT 1);

SET @sql = IF(@constraint_name IS NOT NULL, 
              CONCAT('ALTER TABLE invitation_codes DROP FOREIGN KEY ', @constraint_name), 
              'SELECT "No foreign key constraint found for invitation_codes.created_by"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 invitation_codes created_by 约束
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_created_smart_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 清理 invitation_codes 表的 used_by 约束
SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                       WHERE TABLE_SCHEMA = DATABASE() 
                       AND TABLE_NAME = 'invitation_codes' 
                       AND COLUMN_NAME = 'used_by' 
                       AND REFERENCED_TABLE_NAME = 'auth_users' 
                       LIMIT 1);

SET @sql = IF(@constraint_name IS NOT NULL, 
              CONCAT('ALTER TABLE invitation_codes DROP FOREIGN KEY ', @constraint_name), 
              'SELECT "No foreign key constraint found for invitation_codes.used_by"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 invitation_codes used_by 约束
ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_used_smart_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 清理 user_profiles 表的约束
SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                       WHERE TABLE_SCHEMA = DATABASE() 
                       AND TABLE_NAME = 'user_profiles' 
                       AND COLUMN_NAME = 'user_id' 
                       AND REFERENCED_TABLE_NAME = 'auth_users' 
                       LIMIT 1);

SET @sql = IF(@constraint_name IS NOT NULL, 
              CONCAT('ALTER TABLE user_profiles DROP FOREIGN KEY ', @constraint_name), 
              'SELECT "No foreign key constraint found for user_profiles.user_id"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加 user_profiles 约束
ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_smart_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;








