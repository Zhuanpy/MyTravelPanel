-- 为 tour_products 表添加 country 和 city 字段
-- 执行日期: 2025-10-15
-- 目的: 支持按国家和城市筛选旅游产品

-- MySQL 版本
ALTER TABLE tour_products 
ADD COLUMN country VARCHAR(100) NULL COMMENT '国家' AFTER title,
ADD COLUMN city VARCHAR(100) NULL COMMENT '城市' AFTER country;

-- 为新字段添加索引以提升查询性能
CREATE INDEX idx_tour_products_country ON tour_products(country);
CREATE INDEX idx_tour_products_city ON tour_products(city);
CREATE INDEX idx_tour_products_country_city ON tour_products(country, city);

-- 查看结果
DESCRIBE tour_products;

