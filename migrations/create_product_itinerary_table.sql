-- ========================================
-- 创建 product_itinerary 表（产品行程详情）
-- ========================================

USE travel_panel_new;

-- 创建 product_itinerary 表（参考 tour_itinerary，支持图片上传）
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
    
    -- 外键约束
    CONSTRAINT fk_product_itinerary_product 
        FOREIGN KEY (product_id) REFERENCES travelproducts(id) 
        ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_product_day (product_id, day_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产品行程详情表（参考tour_itinerary）';

-- 验证表结构
DESCRIBE product_itinerary;

SELECT '✅ product_itinerary 表创建成功！' AS Status;

