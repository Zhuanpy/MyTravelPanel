-- 检查和修复公司 logo_path 路径
-- 确保路径格式在 Windows 和 Linux 上都能正常工作

-- 1. 查看当前的 logo_path 值
SELECT 
    id,
    company_name,
    company_name_cn,
    logo_path as '当前路径',
    CASE 
        WHEN logo_path IS NULL THEN '❌ 路径为空'
        WHEN logo_path LIKE '%\\%' THEN '❌ 包含反斜杠，需要修复'
        WHEN logo_path LIKE 'App_new/static/%' THEN '⚠️ 包含App_new/static/前缀，建议移除'
        WHEN logo_path LIKE 'static/%' THEN '⚠️ 包含static/前缀，建议移除'
        WHEN logo_path LIKE '%/%' THEN '✅ 路径格式正确'
        ELSE '⚠️ 需要检查'
    END as '路径状态'
FROM company_info;

-- 2. 修复路径：将反斜杠替换为正斜杠
UPDATE company_info 
SET logo_path = REPLACE(logo_path, '\', '/')
WHERE logo_path LIKE '%\\%';

-- 3. 移除 App_new/static/ 前缀
UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'App_new/static/', '')
WHERE logo_path LIKE 'App_new/static/%';

-- 4. 移除 static/ 前缀
UPDATE company_info 
SET logo_path = REPLACE(logo_path, 'static/', '')
WHERE logo_path LIKE 'static/%';

-- 5. 再次查看修复后的路径
SELECT 
    id,
    company_name,
    company_name_cn,
    logo_path as '修复后的路径',
    CASE 
        WHEN logo_path IS NULL THEN '❌ 路径为空'
        WHEN logo_path LIKE '%/%' AND logo_path NOT LIKE 'static/%' AND logo_path NOT LIKE '%\\%' THEN '✅ 路径格式正确'
        ELSE '⚠️ 仍需检查'
    END as '路径状态'
FROM company_info;

-- 推荐的路径格式示例：
-- ✅ company/logo.png
-- ✅ JE/LOGO.png
-- ✅ images/company_logo.png
-- ❌ static/company/logo.png (不要包含 static/)
-- ❌ App_new/static/company/logo.png (不要包含 App_new/static/)
-- ❌ company\logo.png (不要使用反斜杠)

