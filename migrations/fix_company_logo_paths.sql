-- ========================================
-- 修复 company_info 表中的 logo_path 字段
-- 移除多余的路径前缀
-- ========================================

USE travelindustry;

-- 暂时禁用安全更新模式
SET SQL_SAFE_UPDATES = 0;

-- 查看当前的logo路径
SELECT id, company_name, logo_path AS '修复前路径' FROM company_info;

-- 移除 'App_new/static/' 前缀
UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'App_new/static/', '')
WHERE id > 0 AND logo_path LIKE 'App_new/static/%';

-- 移除 'static/' 前缀
UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'static/', '')
WHERE id > 0 AND logo_path LIKE 'static/%';

-- 标准化路径分隔符（Windows反斜杠转为正斜杠）
UPDATE company_info 
SET logo_path = REPLACE(logo_path, '\\', '/')
WHERE id > 0 AND logo_path LIKE '%\\%';

-- 查看修复后的路径
SELECT id, company_name, logo_path AS '修复后路径' FROM company_info;

-- 恢复安全更新模式
SET SQL_SAFE_UPDATES = 1;

SELECT '✅ company_info logo路径修复完成！' AS Status;

-- 验证说明
-- 正确的格式应该是：company/company_logo_20251018_120000.jpg
-- 或者：images/logo.png
-- 而不是：static/company/... 或 App_new/static/company/...

