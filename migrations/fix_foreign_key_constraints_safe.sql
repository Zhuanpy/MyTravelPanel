-- 安全的修复用户删除时的外键约束问题
-- 此脚本会先检查并删除现有的外键约束，然后添加新的约束

-- 1. 修复 Todo 表的外键约束
-- 先删除可能存在的旧外键约束
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

-- 添加新的外键约束
ALTER TABLE todos 
ADD CONSTRAINT todos_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 2. 修复 InvitationCode 表的外键约束 - created_by
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

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_created_by_fk 
FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 3. 修复 InvitationCode 表的外键约束 - used_by
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

ALTER TABLE invitation_codes 
ADD CONSTRAINT invitation_codes_used_by_fk 
FOREIGN KEY (used_by) REFERENCES auth_users(id) ON DELETE SET NULL;

-- 4. 确保 UserProfile 表的外键约束正确
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

ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_user_id_fk 
FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;

-- 5. 确保 EmailVerificationToken 表的外键约束正确（如果表存在）
SET @table_exists = (SELECT COUNT(*) FROM information_schema.tables 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'email_verification_tokens');

SET @sql = IF(@table_exists > 0, 
              CONCAT('SET @constraint_name = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                     WHERE TABLE_SCHEMA = DATABASE() 
                     AND TABLE_NAME = ''email_verification_tokens'' 
                     AND COLUMN_NAME = ''user_id'' 
                     AND REFERENCED_TABLE_NAME = ''auth_users'' 
                     LIMIT 1);
                     SET @sql = IF(@constraint_name IS NOT NULL, 
                                   CONCAT(''ALTER TABLE email_verification_tokens DROP FOREIGN KEY '', @constraint_name), 
                                   ''SELECT "No foreign key constraint found for email_verification_tokens.user_id"'');
                     PREPARE stmt FROM @sql;
                     EXECUTE stmt;
                     DEALLOCATE PREPARE stmt;
                     
                     ALTER TABLE email_verification_tokens 
                     ADD CONSTRAINT email_verification_tokens_user_id_fk 
                     FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE;'), 
              'SELECT "email_verification_tokens table does not exist, skipping..."');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;







