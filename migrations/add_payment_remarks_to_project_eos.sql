-- 添加付款备注字段到 project_eos 表
ALTER TABLE project_eos ADD COLUMN payment_remarks TEXT NULL COMMENT '付款备注';

