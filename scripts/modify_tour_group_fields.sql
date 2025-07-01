-- 修改tour_group表字段类型和添加新字段
-- 执行日期: 2024-01-01

-- 修改transport字段类型从VARCHAR(100)改为TEXT
ALTER TABLE tour_group MODIFY COLUMN transport TEXT COMMENT '交通工具';

-- 修改meals字段类型从VARCHAR(100)改为TEXT
ALTER TABLE tour_group MODIFY COLUMN meals TEXT COMMENT '用餐安排';

-- 添加包含项目字段
ALTER TABLE tour_group ADD COLUMN included_items TEXT COMMENT '包含项目';

-- 添加不包含项目字段  
ALTER TABLE tour_group ADD COLUMN excluded_items TEXT COMMENT '不包含项目';

-- 添加注意事项字段
ALTER TABLE tour_group ADD COLUMN important_notes TEXT COMMENT '注意事项';

-- 验证字段是否修改成功
DESCRIBE tour_group; 