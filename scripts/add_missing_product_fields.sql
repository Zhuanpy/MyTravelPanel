-- 添加缺失的product_type字段
ALTER TABLE travelproducts 
ADD COLUMN product_type VARCHAR(50) NULL COMMENT '产品类型：跟团游/自由行/定制游';

-- 添加缺失的duration_days字段
ALTER TABLE travelproducts 
ADD COLUMN duration_days INT NULL COMMENT '行程天数';

-- 显示更新后的表结构
DESCRIBE travelproducts; 