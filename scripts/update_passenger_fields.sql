-- Update passenger table fields
ALTER TABLE passengers
    CHANGE COLUMN ticket_price selling_price DECIMAL(10,2) COMMENT '售价',
    CHANGE COLUMN tax cost_price DECIMAL(10,2) COMMENT '成本',
    ADD COLUMN supplier_name VARCHAR(100) COMMENT '供应商名称' AFTER id_number,
    DROP COLUMN phone; 