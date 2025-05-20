-- 添加电子客票号和PNR字段到乘客表
ALTER TABLE passengers ADD COLUMN ticket_number VARCHAR(13) COMMENT '电子客票号';
ALTER TABLE passengers ADD COLUMN pnr VARCHAR(6) COMMENT 'PNR编码'; 