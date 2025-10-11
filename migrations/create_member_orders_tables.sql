-- 创建会员订单相关表
-- 执行时间: YYYY-MM-DD
-- 说明: 创建会员订单系统的所有相关表，使用 member_ 前缀与 staff 订单系统区分

-- 1. 创建会员订单主表
CREATE TABLE IF NOT EXISTS member_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    
    -- 订单基本信息
    service_type VARCHAR(20) NOT NULL,
    service_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 订单状态
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    priority VARCHAR(20) DEFAULT 'normal',
    
    -- 价格信息
    base_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    additional_fees DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'SGD',
    
    -- 时间信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- 客户信息
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(120) NOT NULL,
    customer_phone VARCHAR(20),
    customer_address TEXT,
    
    -- 特殊要求
    special_requirements TEXT,
    notes TEXT
);

-- 创建索引
CREATE INDEX idx_member_orders_order_number ON member_orders(order_number);
CREATE INDEX idx_member_orders_user_id ON member_orders(user_id);
CREATE INDEX idx_member_orders_status ON member_orders(status);
CREATE INDEX idx_member_orders_service_type ON member_orders(service_type);
CREATE INDEX idx_member_orders_created_at ON member_orders(created_at);

-- 2. 创建会员订单项目表
CREATE TABLE IF NOT EXISTS member_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES member_orders(id) ON DELETE CASCADE,
    
    -- 项目信息
    item_name VARCHAR(200) NOT NULL,
    item_description TEXT,
    item_type VARCHAR(50),
    
    -- 数量和价格
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    
    -- 特殊属性
    properties JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_member_order_items_order_id ON member_order_items(order_id);

-- 3. 创建会员订单文档表
CREATE TABLE IF NOT EXISTS member_order_documents (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES member_orders(id) ON DELETE CASCADE,
    
    -- 文档信息
    document_name VARCHAR(200) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    
    -- 状态
    is_verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_member_order_documents_order_id ON member_order_documents(order_id);
CREATE INDEX idx_member_order_documents_document_type ON member_order_documents(document_type);

-- 4. 创建会员订单支付表
CREATE TABLE IF NOT EXISTS member_order_payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES member_orders(id) ON DELETE CASCADE,
    
    -- 支付信息
    payment_method VARCHAR(50) NOT NULL,
    payment_reference VARCHAR(100),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'SGD',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',
    transaction_id VARCHAR(100),
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_member_order_payments_order_id ON member_order_payments(order_id);
CREATE INDEX idx_member_order_payments_status ON member_order_payments(status);
CREATE INDEX idx_member_order_payments_payment_reference ON member_order_payments(payment_reference);

-- 5. 创建会员服务模板表
CREATE TABLE IF NOT EXISTS member_service_templates (
    id SERIAL PRIMARY KEY,
    
    -- 服务基本信息
    service_type VARCHAR(20) NOT NULL,
    service_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 价格信息
    base_price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'SGD',
    
    -- 处理信息
    processing_time VARCHAR(100),
    requirements TEXT,
    required_documents JSONB,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_member_service_templates_service_type ON member_service_templates(service_type);
CREATE INDEX idx_member_service_templates_is_active ON member_service_templates(is_active);
CREATE INDEX idx_member_service_templates_is_featured ON member_service_templates(is_featured);

-- 添加注释
COMMENT ON TABLE member_orders IS '会员订单主表';
COMMENT ON TABLE member_order_items IS '会员订单项目表';
COMMENT ON TABLE member_order_documents IS '会员订单文档表';
COMMENT ON TABLE member_order_payments IS '会员订单支付表';
COMMENT ON TABLE member_service_templates IS '会员服务模板表';

-- 添加约束
ALTER TABLE member_orders ADD CONSTRAINT chk_member_orders_status 
    CHECK (status IN ('draft', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'refunded'));

ALTER TABLE member_orders ADD CONSTRAINT chk_member_orders_priority 
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'));

ALTER TABLE member_order_payments ADD CONSTRAINT chk_member_order_payments_status 
    CHECK (status IN ('pending', 'completed', 'failed', 'refunded'));

-- 创建更新时间触发器函数（如果不存在）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为会员订单主表添加更新时间触发器
DROP TRIGGER IF EXISTS update_member_orders_updated_at ON member_orders;
CREATE TRIGGER update_member_orders_updated_at
    BEFORE UPDATE ON member_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为会员服务模板表添加更新时间触发器
DROP TRIGGER IF EXISTS update_member_service_templates_updated_at ON member_service_templates;
CREATE TRIGGER update_member_service_templates_updated_at
    BEFORE UPDATE ON member_service_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入示例服务模板数据
INSERT INTO member_service_templates (service_type, service_name, description, base_price, processing_time, requirements, required_documents, is_active, is_featured)
VALUES 
    ('visa', '新加坡旅游签证', '为中国公民提供新加坡旅游签证办理服务', 50.00, '3-5个工作日', '护照有效期至少6个月，提供完整材料', 
     '["护照原件", "2张2寸白底彩色照片", "签证申请表", "往返机票预订单", "酒店预订单"]'::jsonb, TRUE, TRUE),
    
    ('visa', '泰国旅游签证', '为中国公民提供泰国旅游签证办理服务', 40.00, '2-3个工作日', '护照有效期至少6个月，提供完整材料', 
     '["护照原件", "2张2寸白底彩色照片", "签证申请表", "往返机票预订单"]'::jsonb, TRUE, FALSE),
    
    ('flight', '国际机票预订', '提供全球航线机票预订服务', 0.00, '即时出票', '提供准确的乘客信息和航班需求', 
     '["护照信息", "联系方式"]'::jsonb, TRUE, FALSE),
    
    ('hotel', '酒店预订服务', '提供全球酒店预订服务', 0.00, '即时确认', '提供入住日期和要求', 
     '["入住人信息", "特殊要求"]'::jsonb, TRUE, FALSE),
    
    ('tour', '东南亚旅游套餐', '精心设计的东南亚旅游线路', 999.00, '提前3天预订', '至少提前3天预订，提供完整的旅客信息', 
     '["护照信息", "紧急联系人", "特殊需求说明"]'::jsonb, TRUE, TRUE);

-- 输出创建结果
SELECT 'Member orders tables created successfully!' AS status;
