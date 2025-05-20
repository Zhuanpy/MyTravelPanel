-- 添加ref_type_id字段到project_refs表
ALTER TABLE project_refs
ADD COLUMN ref_type_id INT NOT NULL AFTER project_id,
ADD CONSTRAINT fk_ref_type
    FOREIGN KEY (ref_type_id)
    REFERENCES business_types(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE; 