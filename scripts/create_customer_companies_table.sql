-- 创建客户公司表
CREATE TABLE IF NOT EXISTS customer_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(100) NOT NULL UNIQUE,
    company_code VARCHAR(50),
    contact_person VARCHAR(50),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(100),
    address TEXT,
    industry VARCHAR(50),
    company_size VARCHAR(20),
    credit_limit DECIMAL(15,2),
    currency VARCHAR(10) DEFAULT 'SGD',
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    remarks TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_customer_companies_company_name ON customer_companies(company_name);
CREATE INDEX IF NOT EXISTS idx_customer_companies_status ON customer_companies(status);
CREATE INDEX IF NOT EXISTS idx_customer_companies_created_at ON customer_companies(created_at);

-- 添加外键约束到project_headers表
ALTER TABLE project_headers ADD COLUMN company_id INTEGER;
ALTER TABLE project_headers ADD CONSTRAINT fk_project_headers_company_id 
    FOREIGN KEY (company_id) REFERENCES customer_companies(id);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_project_headers_company_id ON project_headers(company_id); 