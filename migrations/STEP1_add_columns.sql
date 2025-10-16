-- ========================================
-- 步骤 1: 添加新列到 travelproducts 和 tour_project
-- 执行前确保已备份数据库！
-- ========================================

USE travel_panel_new;

-- ========================================
-- 1. travelproducts 表 - 添加新列
-- ========================================

-- 供应商关联
ALTER TABLE travelproducts ADD COLUMN supplier_id INT NULL COMMENT '供应商ID';

-- 产品编号
ALTER TABLE travelproducts ADD COLUMN product_code VARCHAR(50) NULL COMMENT '产品编号';

-- 国家
ALTER TABLE travelproducts ADD COLUMN country VARCHAR(100) NULL COMMENT '国家';

-- 住宿晚数
ALTER TABLE travelproducts ADD COLUMN duration_nights INT NULL COMMENT '住宿晚数';

-- 标签
ALTER TABLE travelproducts ADD COLUMN tags TEXT NULL COMMENT '标签JSON';

-- 封面图
ALTER TABLE travelproducts ADD COLUMN cover_image VARCHAR(500) NULL COMMENT '封面图';

-- 图片库
ALTER TABLE travelproducts ADD COLUMN gallery_images TEXT NULL COMMENT '图片库JSON';

-- 是否精选
ALTER TABLE travelproducts ADD COLUMN is_featured TINYINT(1) DEFAULT 0 COMMENT '是否精选';

-- 有效开始日期
ALTER TABLE travelproducts ADD COLUMN valid_from DATE NULL COMMENT '有效开始日期';

-- 版本号
ALTER TABLE travelproducts ADD COLUMN version INT DEFAULT 1 COMMENT '版本号';

-- 父产品ID
ALTER TABLE travelproducts ADD COLUMN parent_product_id INT NULL COMMENT '父产品ID';

-- 创建人
ALTER TABLE travelproducts ADD COLUMN created_by VARCHAR(100) NULL COMMENT '创建人';

-- ========================================
-- 2. tour_project 表 - 添加新列
-- ========================================

-- 基础产品ID
ALTER TABLE tour_project ADD COLUMN base_product_id INT NULL COMMENT '基于哪个产品模板';

-- 货币单位
ALTER TABLE tour_project ADD COLUMN currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币单位';

-- 创建人
ALTER TABLE tour_project ADD COLUMN created_by VARCHAR(100) NULL COMMENT '创建人';

-- ========================================
-- 验证结果
-- ========================================

SELECT '✅ Step 1 Completed: Columns Added Successfully!' AS Status;

-- 查看新增的列
DESCRIBE travelproducts;
DESCRIBE tour_project;

