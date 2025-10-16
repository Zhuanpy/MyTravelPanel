-- ========================================
-- 为 product_itinerary 表添加图片字段（安全版本）
-- ========================================

USE travel_panel_new;

-- 方案1：如果表不存在，直接创建完整表
CREATE TABLE IF NOT EXISTS product_itinerary (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    product_id INT NOT NULL COMMENT '产品ID',
    day_number INT NOT NULL COMMENT '第几天',
    day_title TEXT NOT NULL COMMENT '行程安排',
    image1 VARCHAR(500) COMMENT '图片1路径',
    image2 VARCHAR(500) COMMENT '图片2路径',
    image3 VARCHAR(500) COMMENT '图片3路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    CONSTRAINT fk_product_itinerary_product 
        FOREIGN KEY (product_id) REFERENCES travelproducts(id) 
        ON DELETE CASCADE,
    
    INDEX idx_product_day (product_id, day_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产品行程详情表';

-- 方案2：如果表已存在但没有图片字段，则添加
-- 注意：如果字段已存在会报错，这是正常的，可以忽略

SET @sql1 = 'ALTER TABLE product_itinerary ADD COLUMN image1 VARCHAR(500) COMMENT ''图片1路径'' AFTER day_title';
SET @sql2 = 'ALTER TABLE product_itinerary ADD COLUMN image2 VARCHAR(500) COMMENT ''图片2路径'' AFTER image1';
SET @sql3 = 'ALTER TABLE product_itinerary ADD COLUMN image3 VARCHAR(500) COMMENT ''图片3路径'' AFTER image2';

-- 尝试添加 image1
SET @column_exists = (
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = 'travel_panel_new' 
        AND TABLE_NAME = 'product_itinerary' 
        AND COLUMN_NAME = 'image1'
);

-- 如果 image1 不存在，执行添加
SELECT IF(@column_exists = 0, 
    '需要添加 image1 字段', 
    'image1 字段已存在'
) AS image1_status;

-- 添加字段（如果不存在）
SET @add_image1 = IF(@column_exists = 0, @sql1, 'SELECT ''image1 already exists''');
PREPARE stmt1 FROM @add_image1;
EXECUTE stmt1;
DEALLOCATE PREPARE stmt1;

-- 检查 image2
SET @column_exists = (
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = 'travel_panel_new' 
        AND TABLE_NAME = 'product_itinerary' 
        AND COLUMN_NAME = 'image2'
);

SET @add_image2 = IF(@column_exists = 0, @sql2, 'SELECT ''image2 already exists''');
PREPARE stmt2 FROM @add_image2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 检查 image3
SET @column_exists = (
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = 'travel_panel_new' 
        AND TABLE_NAME = 'product_itinerary' 
        AND COLUMN_NAME = 'image3'
);

SET @add_image3 = IF(@column_exists = 0, @sql3, 'SELECT ''image3 already exists''');
PREPARE stmt3 FROM @add_image3;
EXECUTE stmt3;
DEALLOCATE PREPARE stmt3;

-- 验证最终表结构
DESCRIBE product_itinerary;

SELECT '✅ product_itinerary 表已更新完成！' AS Status;

