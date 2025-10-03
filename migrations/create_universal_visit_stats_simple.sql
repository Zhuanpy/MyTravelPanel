-- 创建通用产品访问统计表 (MySQL版本 - 简化版)
CREATE TABLE product_visit_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_type VARCHAR(50) NOT NULL COMMENT '产品类型：visa, tour, flight, hotel等',
    product_id INT NOT NULL COMMENT '产品ID（对应各产品表的主键）',
    product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
    product_category VARCHAR(100) COMMENT '产品分类（如国家、地区等）',
    visitor_ip VARCHAR(45),
    user_agent TEXT,
    referer TEXT,
    visit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    additional_data TEXT COMMENT 'JSON格式的额外数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建索引提高查询性能
CREATE INDEX idx_product_visit_stats_type_id ON product_visit_stats(product_type, product_id);
CREATE INDEX idx_product_visit_stats_visit_time ON product_visit_stats(visit_time);
CREATE INDEX idx_product_visit_stats_session_id ON product_visit_stats(session_id);
CREATE INDEX idx_product_visit_stats_product_type ON product_visit_stats(product_type);
CREATE INDEX idx_product_visit_stats_created_at ON product_visit_stats(created_at);
