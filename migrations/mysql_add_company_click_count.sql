-- MySQL脚本：添加公司点击次数字段
-- 用于统计公司被点击的次数，点击次数越多排序越靠前

-- ========================================
-- 1. 检查当前表结构
-- ========================================
DESCRIBE customer_companies;

-- ========================================
-- 2. 添加点击次数字段
-- ========================================
ALTER TABLE customer_companies 
ADD COLUMN click_count INT DEFAULT 0 COMMENT '点击次数';

-- ========================================
-- 3. 添加最后点击时间字段
-- ========================================
ALTER TABLE customer_companies 
ADD COLUMN last_clicked_at DATETIME NULL COMMENT '最后点击时间';

-- ========================================
-- 4. 验证字段添加成功
-- ========================================
DESCRIBE customer_companies;

-- ========================================
-- 5. 检查数据
-- ========================================
SELECT 
    id,
    company_name,
    click_count,
    last_clicked_at,
    created_at,
    updated_at
FROM customer_companies 
ORDER BY created_at DESC 
LIMIT 5;

-- ========================================
-- 6. 更新现有记录的点击次数（可选）
-- ========================================
-- 如果需要为现有记录设置初始点击次数，可以执行以下语句
-- UPDATE customer_companies SET click_count = 0 WHERE click_count IS NULL;

-- ========================================
-- 7. 验证更新结果
-- ========================================
SELECT 
    COUNT(*) as total_companies,
    COUNT(CASE WHEN click_count > 0 THEN 1 END) as companies_with_clicks,
    AVG(click_count) as avg_clicks,
    MAX(click_count) as max_clicks
FROM customer_companies;
