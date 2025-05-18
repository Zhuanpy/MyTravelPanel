-- 删除现有表
DROP TABLE IF EXISTS project_refs;

-- 重新创建表
CREATE TABLE project_refs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    ref_type_id INT NOT NULL,
    ref_number VARCHAR(30) NOT NULL UNIQUE,
    description VARCHAR(200) NOT NULL,
    status ENUM('draft', 'processing', 'completed', 'cancelled') NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_project_ref
        FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_ref_type
        FOREIGN KEY (ref_type_id)
        REFERENCES business_types(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 