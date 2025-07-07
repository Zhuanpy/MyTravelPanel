-- 添加product_type字段到travelproducts表
ALTER TABLE travelproducts 
ADD COLUMN product_type VARCHAR(50) NULL COMMENT '产品类型：跟团游/自由行/定制游';

-- 添加其他可能缺失的字段
ALTER TABLE travelproducts 
ADD COLUMN duration_days INT NULL COMMENT '行程天数';

ALTER TABLE travelproducts 
ADD COLUMN departure_city VARCHAR(100) NULL COMMENT '出发城市';

ALTER TABLE travelproducts 
ADD COLUMN destination_city VARCHAR(100) NULL COMMENT '目的地城市';

ALTER TABLE travelproducts 
ADD COLUMN min_pax INT NULL COMMENT '最少成团人数';

ALTER TABLE travelproducts 
ADD COLUMN max_pax INT NULL COMMENT '最大成团人数';

ALTER TABLE travelproducts 
ADD COLUMN suitable_season VARCHAR(200) NULL COMMENT '适合季节';

ALTER TABLE travelproducts 
ADD COLUMN difficulty_level VARCHAR(50) NULL COMMENT '难度等级：简单/中等/困难';

ALTER TABLE travelproducts 
ADD COLUMN product_status VARCHAR(50) DEFAULT 'active' COMMENT '产品状态：active/inactive/draft';

ALTER TABLE travelproducts 
ADD COLUMN single_room_supplement FLOAT NULL COMMENT '单房差';

ALTER TABLE travelproducts 
ADD COLUMN child_price FLOAT NULL COMMENT '儿童价格';

ALTER TABLE travelproducts 
ADD COLUMN infant_price FLOAT NULL COMMENT '婴儿价格';

ALTER TABLE travelproducts 
ADD COLUMN currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位';

ALTER TABLE travelproducts 
ADD COLUMN product_description TEXT NULL COMMENT '产品描述';

ALTER TABLE travelproducts 
ADD COLUMN highlights TEXT NULL COMMENT '产品亮点';

ALTER TABLE travelproducts 
ADD COLUMN included_services TEXT NULL COMMENT '包含服务';

ALTER TABLE travelproducts 
ADD COLUMN excluded_services TEXT NULL COMMENT '不包含服务';

ALTER TABLE travelproducts 
ADD COLUMN important_notes TEXT NULL COMMENT '重要提示';

ALTER TABLE travelproducts 
ADD COLUMN contact_person VARCHAR(100) NULL COMMENT '联系人';

ALTER TABLE travelproducts 
ADD COLUMN contact_phone VARCHAR(50) NULL COMMENT '联系电话';

ALTER TABLE travelproducts 
ADD COLUMN contact_email VARCHAR(100) NULL COMMENT '联系邮箱';

ALTER TABLE travelproducts 
ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间';

-- 显示更新后的表结构
DESCRIBE travelproducts; 