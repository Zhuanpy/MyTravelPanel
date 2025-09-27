-- 为visa_countries表添加国旗文件字段
ALTER TABLE visa_countries 
ADD COLUMN flag_file VARCHAR(255) NULL COMMENT '国旗文件名';
