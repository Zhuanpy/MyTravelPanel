-- Add supplier field to flight_orders table
ALTER TABLE flight_orders
ADD COLUMN supplier_name VARCHAR(100) COMMENT '供应商名称' AFTER contact_name; 