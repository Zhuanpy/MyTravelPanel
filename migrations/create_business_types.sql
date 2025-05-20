-- 创建业务类型表
CREATE TABLE business_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '类型名称',
    code VARCHAR(20) NOT NULL UNIQUE COMMENT '类型代码',
    description VARCHAR(200) COMMENT '描述',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    sort_order INT DEFAULT 0 COMMENT '排序顺序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务类型表';

-- 修改项目REF表，添加业务类型外键
ALTER TABLE project_refs
    DROP COLUMN ref_type,
    ADD COLUMN ref_type_id INT NOT NULL COMMENT 'REF类型ID',
    ADD CONSTRAINT fk_ref_type FOREIGN KEY (ref_type_id) REFERENCES business_types(id); 