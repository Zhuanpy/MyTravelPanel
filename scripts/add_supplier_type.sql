-- Add supplier type field to suppliers table
ALTER TABLE suppliers
ADD COLUMN supplier_type ENUM('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other') 
NOT NULL DEFAULT 'other' COMMENT '供应商类型' AFTER name; 