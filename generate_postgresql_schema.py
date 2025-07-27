#!/usr/bin/env python3
"""
根据项目模型生成PostgreSQL兼容的数据库模式
"""

def generate_postgresql_schema():
    """生成PostgreSQL兼容的数据库模式"""
    
    schema_sql = """
-- PostgreSQL 数据库模式生成脚本
-- 基于 MyTravelPanel 项目的 SQLAlchemy 模型

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- ========================================
-- 1. 用户和账户相关表
-- ========================================

-- 用户表
CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL PRIMARY KEY,
    "username" VARCHAR(80) UNIQUE NOT NULL,
    "email" VARCHAR(120) UNIQUE NOT NULL,
    "password_hash" VARCHAR(128),
    "role" VARCHAR(20) DEFAULT 'user',
    "is_active" BOOLEAN DEFAULT TRUE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "last_login" TIMESTAMP WITH TIME ZONE,
    "full_name" VARCHAR(100),
    "phone" VARCHAR(20),
    "department" VARCHAR(100),
    "position" VARCHAR(100)
);

-- 账户表
CREATE TABLE IF NOT EXISTS "accounts" (
    "id" SERIAL PRIMARY KEY,
    "platform" VARCHAR(100) NOT NULL,
    "website_url" VARCHAR(2000),
    "username" VARCHAR(100) NOT NULL,
    "password" VARCHAR(100) NOT NULL,
    "category" VARCHAR(50),
    "owner" VARCHAR(100),
    "country" VARCHAR(100),
    "region" VARCHAR(100),
    "description" TEXT,
    "notes" TEXT,
    "file_materials" TEXT,
    "additional_info" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "click_count" INTEGER DEFAULT 0
);

-- ========================================
-- 2. 业务类型和供应商表
-- ========================================

-- 业务类型表
CREATE TABLE IF NOT EXISTS "business_types" (
    "id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 供应商表
CREATE TABLE IF NOT EXISTS "suppliers" (
    "supplier_id" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "supplier_type" VARCHAR(20) NOT NULL DEFAULT 'other' CHECK (supplier_type IN ('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other')),
    "contact_person" VARCHAR(100),
    "phone" VARCHAR(20),
    "email" VARCHAR(255),
    "address" TEXT,
    "country" VARCHAR(50),
    "region" VARCHAR(50),
    "status" VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "last_updated" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT
);

-- 供应商数据表
CREATE TABLE IF NOT EXISTS "supplier_data" (
    "id" SERIAL PRIMARY KEY,
    "create_date" TIMESTAMP WITH TIME ZONE,
    "last_updated" TIMESTAMP WITH TIME ZONE,
    "name" VARCHAR(255),
    "supplier_type" VARCHAR(20) NOT NULL DEFAULT 'other' CHECK (supplier_type IN ('visa', 'flight', 'hotel', 'transport', 'local_operator', 'other')),
    "address" VARCHAR(255),
    "contact_info" VARCHAR(255),
    "contact_person" VARCHAR(20),
    "status" VARCHAR(20) DEFAULT 'active',
    "country" VARCHAR(50),
    "region" VARCHAR(50),
    "rating" FLOAT,
    "notes" TEXT
);

-- ========================================
-- 3. 项目管理相关表
-- ========================================

-- 客户公司表
CREATE TABLE IF NOT EXISTS "customer_companies" (
    "id" SERIAL PRIMARY KEY,
    "company_name" VARCHAR(100) NOT NULL UNIQUE,
    "company_code" VARCHAR(50),
    "contact_person" VARCHAR(50),
    "contact_phone" VARCHAR(20),
    "contact_email" VARCHAR(100),
    "address" TEXT,
    "industry" VARCHAR(50),
    "company_size" VARCHAR(20),
    "credit_limit" NUMERIC(15, 2),
    "currency" VARCHAR(10) DEFAULT 'SGD',
    "status" VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    "remarks" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "created_by" VARCHAR(50)
);

-- 客户表
CREATE TABLE IF NOT EXISTS "customers" (
    "id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "phone" VARCHAR(20),
    "email" VARCHAR(100),
    "id_number" VARCHAR(30),
    "id_type" VARCHAR(20),
    "address" TEXT,
    "company" VARCHAR(100),
    "contact_person" VARCHAR(50),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 项目主表
CREATE TABLE IF NOT EXISTS "project_headers" (
    "id" SERIAL PRIMARY KEY,
    "hid" VARCHAR(20) UNIQUE NOT NULL,
    "desc" VARCHAR(200),
    "company_id" INTEGER REFERENCES "customer_companies"("id"),
    "limit" VARCHAR(50),
    "contact" VARCHAR(50),
    "dept" VARCHAR(50),
    "staff_id" INTEGER,
    "staff_name" VARCHAR(50),
    "currency" VARCHAR(10),
    "leader_name" VARCHAR(100),
    "type" VARCHAR(50),
    "source" VARCHAR(50),
    "country" VARCHAR(50),
    "status" VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "last_updated_by" VARCHAR(50),
    "remarks" TEXT
);

-- 项目明细表
CREATE TABLE IF NOT EXISTS "project_refs" (
    "id" SERIAL PRIMARY KEY,
    "ref_number" VARCHAR(50) NOT NULL,
    "header_id" INTEGER NOT NULL REFERENCES "project_headers"("id") ON DELETE CASCADE,
    "name" VARCHAR(200),
    "description" TEXT,
    "ref_type_id" INTEGER REFERENCES "business_types"("id"),
    "supplier_id" INTEGER REFERENCES "suppliers"("supplier_id"),
    "cost_price" NUMERIC(15, 2),
    "selling_price" NUMERIC(15, 2),
    "currency" VARCHAR(10) DEFAULT 'SGD',
    "status" VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    "remarks" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 项目EO表
CREATE TABLE IF NOT EXISTS "project_eos" (
    "id" SERIAL PRIMARY KEY,
    "ref_id" INTEGER NOT NULL REFERENCES "project_refs"("id"),
    "eo_number" VARCHAR(30) UNIQUE NOT NULL,
    "name" VARCHAR(100),
    "supplier_type" VARCHAR(20) DEFAULT 'other',
    "supplier_id" INTEGER REFERENCES "suppliers"("supplier_id"),
    "external_system" VARCHAR(50),
    "external_status" VARCHAR(50),
    "external_reference" VARCHAR(100),
    "amount" NUMERIC(15, 2) DEFAULT 0,
    "currency" VARCHAR(10) DEFAULT 'SGD',
    "remarks" TEXT,
    "status" VARCHAR(20) DEFAULT 'confirmed',
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 4. 航班相关表
-- ========================================

-- 机场数据表
CREATE TABLE IF NOT EXISTS "airport_data" (
    "id" SERIAL PRIMARY KEY,
    "airport_IATA" VARCHAR(3) UNIQUE NOT NULL,
    "city_name" VARCHAR(100) NOT NULL,
    "airport_name_cn" VARCHAR(100) NOT NULL,
    "airport_name_en" VARCHAR(100),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 航班订单表
CREATE TABLE IF NOT EXISTS "flight_orders" (
    "id" SERIAL PRIMARY KEY,
    "order_number" VARCHAR(50) UNIQUE NOT NULL,
    "hid_number" VARCHAR(50),
    "project_header_id" INTEGER REFERENCES "project_headers"("id"),
    "project_ref_id" INTEGER REFERENCES "project_refs"("id"),
    "passenger_name" VARCHAR(100) NOT NULL,
    "contact_person" VARCHAR(100),
    "contact_phone" VARCHAR(20),
    "contact_name" VARCHAR(50) NOT NULL,
    "supplier_name" VARCHAR(100),
    "departure_date" DATE NOT NULL,
    "itinerary" VARCHAR(200),
    "departure_city" VARCHAR(50),
    "arrival_city" VARCHAR(50),
    "airline" VARCHAR(50),
    "flight_number" VARCHAR(20),
    "departure_time" TIMESTAMP WITH TIME ZONE,
    "arrival_time" TIMESTAMP WITH TIME ZONE,
    "cabin_class" VARCHAR(20),
    "is_transit" BOOLEAN DEFAULT FALSE,
    "transit_info" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 乘客表
CREATE TABLE IF NOT EXISTS "passengers" (
    "id" SERIAL PRIMARY KEY,
    "order_id" INTEGER NOT NULL REFERENCES "flight_orders"("id") ON DELETE CASCADE,
    "name" VARCHAR(50) NOT NULL,
    "passenger_type" VARCHAR(10) NOT NULL DEFAULT 'adult',
    "selling_price" NUMERIC(10, 2),
    "cost_price" NUMERIC(10, 2),
    "phone" VARCHAR(20),
    "ticket_number" VARCHAR(13),
    "pnr" VARCHAR(6)
);

-- 航段表
CREATE TABLE IF NOT EXISTS "flight_segments" (
    "id" SERIAL PRIMARY KEY,
    "order_id" INTEGER NOT NULL REFERENCES "flight_orders"("id") ON DELETE CASCADE,
    "flight_number" VARCHAR(10) NOT NULL,
    "departure_airport" VARCHAR(3) NOT NULL,
    "arrival_airport" VARCHAR(3) NOT NULL,
    "departure_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "arrival_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "cabin_class" VARCHAR(20) NOT NULL,
    "cabin_code" VARCHAR(2) NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending'
);

-- ========================================
-- 5. 签证相关表
-- ========================================

-- 签证国家表
CREATE TABLE IF NOT EXISTS "visa_countries" (
    "id" SERIAL PRIMARY KEY,
    "country_name_CN" VARCHAR(100) UNIQUE NOT NULL,
    "country_name_EN" VARCHAR(100) UNIQUE NOT NULL,
    "country_code" VARCHAR(3) UNIQUE NOT NULL
);

-- 新加坡身份表
CREATE TABLE IF NOT EXISTS "visa_singapore_identity" (
    "id" SERIAL PRIMARY KEY,
    "identity_zh" VARCHAR(50) UNIQUE NOT NULL,
    "identity_en" VARCHAR(100) UNIQUE NOT NULL,
    "remarks" TEXT
);

-- 签证类型表
CREATE TABLE IF NOT EXISTS "visa_types" (
    "id" SERIAL PRIMARY KEY,
    "visa_type" VARCHAR(50) NOT NULL,
    "processing_time" VARCHAR(200) NOT NULL,
    "fee" VARCHAR(200) NOT NULL,
    "country_id" INTEGER NOT NULL REFERENCES "visa_countries"("id")
);

-- 签证类型与身份关联表
CREATE TABLE IF NOT EXISTS "visa_type_identities" (
    "visa_type_id" INTEGER NOT NULL REFERENCES "visa_types"("id") ON DELETE CASCADE,
    "identity_id" INTEGER NOT NULL REFERENCES "visa_singapore_identity"("id") ON DELETE CASCADE,
    PRIMARY KEY ("visa_type_id", "identity_id")
);

-- 签证文档列表表
CREATE TABLE IF NOT EXISTS "visa_documents_list" (
    "id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) UNIQUE NOT NULL,
    "description" TEXT,
    "category" VARCHAR(50)
);

-- 签证文档请求表
CREATE TABLE IF NOT EXISTS "visa_documents_request" (
    "id" SERIAL PRIMARY KEY,
    "visa_type_id" INTEGER NOT NULL REFERENCES "visa_types"("id") ON DELETE CASCADE,
    "singapore_identity_id" INTEGER REFERENCES "visa_singapore_identity"("id") ON DELETE CASCADE,
    "additional_info" TEXT
);

-- 签证文档关联表
CREATE TABLE IF NOT EXISTS "visa_document_documents" (
    "visa_document_id" INTEGER NOT NULL REFERENCES "visa_documents_request"("id") ON DELETE CASCADE,
    "document_id" INTEGER NOT NULL REFERENCES "visa_documents_list"("id") ON DELETE CASCADE,
    "responsible_party" VARCHAR(20) DEFAULT 'FOR_APPLICATION',
    PRIMARY KEY ("visa_document_id", "document_id")
);

-- 签证链接表
CREATE TABLE IF NOT EXISTS "visa_type_links" (
    "id" SERIAL PRIMARY KEY,
    "visa_type_id" INTEGER NOT NULL REFERENCES "visa_types"("id") ON DELETE CASCADE,
    "visa_countries_id" INTEGER REFERENCES "visa_countries"("id") ON DELETE CASCADE,
    "name" VARCHAR(50) NOT NULL,
    "link" TEXT
);

-- 签证项目表
CREATE TABLE IF NOT EXISTS "visa_projects" (
    "id" SERIAL PRIMARY KEY,
    "project_folder_name" VARCHAR(100) NOT NULL,
    "created_date" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "visa_status" VARCHAR(50) NOT NULL DEFAULT '待递交',
    "estimated_date" DATE,
    "visa_type" VARCHAR(50),
    "applicant_name" VARCHAR(100),
    "contact_name" VARCHAR(100),
    "remarks" TEXT,
    "hid_or_serial" VARCHAR(100),
    "singapore_status" VARCHAR(50),
    "header_id" INTEGER REFERENCES "project_headers"("id"),
    "ref_id" INTEGER REFERENCES "project_refs"("id")
);

-- 签证项目文档状态表
CREATE TABLE IF NOT EXISTS "visa_project_document_status" (
    "id" SERIAL PRIMARY KEY,
    "project_id" INTEGER NOT NULL REFERENCES "visa_projects"("id") ON DELETE CASCADE,
    "document_name" VARCHAR(200) NOT NULL,
    "document_type" VARCHAR(50) NOT NULL,
    "is_ready" BOOLEAN DEFAULT FALSE,
    "notes" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 6. 旅游产品相关表
-- ========================================

-- 旅游产品表
CREATE TABLE IF NOT EXISTS "travelproducts" (
    "id" SERIAL PRIMARY KEY,
    "city_name" VARCHAR(100) NOT NULL,
    "company_name" VARCHAR(100) NOT NULL,
    "product_name" VARCHAR(100) NOT NULL,
    "created_at" DATE DEFAULT CURRENT_DATE,
    "valid_until" DATE,
    "product_type" VARCHAR(50),
    "duration_days" INTEGER,
    "departure_city" VARCHAR(100),
    "destination_city" VARCHAR(100),
    "min_pax" INTEGER,
    "max_pax" INTEGER,
    "suitable_season" VARCHAR(200),
    "difficulty_level" VARCHAR(50),
    "product_status" VARCHAR(50) DEFAULT 'active',
    "base_price" FLOAT,
    "single_room_supplement" FLOAT,
    "child_price" FLOAT,
    "infant_price" FLOAT,
    "product_description" TEXT,
    "highlights" TEXT,
    "included_services" TEXT,
    "excluded_services" TEXT,
    "important_notes" TEXT,
    "contact_person" VARCHAR(100),
    "contact_phone" VARCHAR(20),
    "contact_email" VARCHAR(100)
);

-- 旅游项目表
CREATE TABLE IF NOT EXISTS "tour_project" (
    "id" SERIAL PRIMARY KEY,
    "project_name" VARCHAR(100) NOT NULL,
    "project_hid" VARCHAR(255),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "project_status" VARCHAR(50) NOT NULL,
    "folder_name" VARCHAR(100) NOT NULL,
    "contact_person" VARCHAR(100) NOT NULL,
    "contact_info" VARCHAR(100) NOT NULL,
    "remarks" TEXT,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "project_type" VARCHAR(50),
    "budget" FLOAT,
    "departure_date" DATE
);

-- 旅游团表
CREATE TABLE IF NOT EXISTS "tour_group" (
    "id" SERIAL PRIMARY KEY,
    "title" VARCHAR(200) NOT NULL,
    "departure_date" DATE NOT NULL,
    "return_date" DATE NOT NULL,
    "pax" INTEGER NOT NULL,
    "agency" VARCHAR(200),
    "operator" VARCHAR(200),
    "hotel_info" VARCHAR(500),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "project_id" INTEGER NOT NULL REFERENCES "tour_project"("id"),
    "project_type" VARCHAR(50),
    "created_by" VARCHAR(100),
    "group_code" VARCHAR(100),
    "group_status" VARCHAR(50),
    "transport" TEXT,
    "meals" TEXT,
    "attractions" TEXT,
    "included_items" TEXT,
    "excluded_items" TEXT,
    "important_notes" TEXT
);

-- ========================================
-- 7. 套餐预算相关表
-- ========================================

-- 套餐预算主表
CREATE TABLE IF NOT EXISTS "package_budget_header" (
    "id" SERIAL PRIMARY KEY,
    "package_name" VARCHAR(255) NOT NULL,
    "adult_count" INTEGER NOT NULL,
    "child_count" INTEGER NOT NULL,
    "currency" VARCHAR(10) DEFAULT 'SGD',
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "created_by" VARCHAR(50),
    "remarks" TEXT,
    "status" VARCHAR(20) DEFAULT 'draft',
    "is_template" BOOLEAN DEFAULT FALSE
);

-- 套餐预算明细表
CREATE TABLE IF NOT EXISTS "package_budget_items" (
    "id" SERIAL PRIMARY KEY,
    "header_id" INTEGER NOT NULL REFERENCES "package_budget_header"("id") ON DELETE CASCADE,
    "item_name" VARCHAR(255) NOT NULL,
    "item_type" VARCHAR(50) NOT NULL,
    "adult_price" NUMERIC(10, 2) DEFAULT 0,
    "child_price" NUMERIC(10, 2) DEFAULT 0,
    "adult_count" INTEGER DEFAULT 0,
    "child_count" INTEGER DEFAULT 0,
    "adult_subtotal" NUMERIC(10, 2) DEFAULT 0,
    "child_subtotal" NUMERIC(10, 2) DEFAULT 0,
    "subtotal" NUMERIC(10, 2) DEFAULT 0,
    "remarks" TEXT,
    "sort_order" INTEGER DEFAULT 0
);

-- ========================================
-- 8. 工具类表
-- ========================================

-- 任务表
CREATE TABLE IF NOT EXISTS "tasks" (
    "id" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "remaining_time" INTEGER DEFAULT 600,
    "status" VARCHAR(20) DEFAULT 'stopped'
);

-- 待办事项表
CREATE TABLE IF NOT EXISTS "todos" (
    "id" SERIAL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "is_completed" BOOLEAN DEFAULT FALSE,
    "due_date" TIMESTAMP WITH TIME ZONE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "priority" INTEGER DEFAULT 2,
    "user_id" INTEGER REFERENCES "users"("id")
);

-- ========================================
-- 9. 创建索引
-- ========================================

-- 用户表索引
CREATE INDEX IF NOT EXISTS "idx_users_username" ON "users"("username");
CREATE INDEX IF NOT EXISTS "idx_users_email" ON "users"("email");
CREATE INDEX IF NOT EXISTS "idx_users_role" ON "users"("role");

-- 账户表索引
CREATE INDEX IF NOT EXISTS "idx_accounts_platform" ON "accounts"("platform");
CREATE INDEX IF NOT EXISTS "idx_accounts_category" ON "accounts"("category");
CREATE INDEX IF NOT EXISTS "idx_accounts_owner" ON "accounts"("owner");

-- 供应商表索引
CREATE INDEX IF NOT EXISTS "idx_suppliers_name" ON "suppliers"("name");
CREATE INDEX IF NOT EXISTS "idx_suppliers_type" ON "suppliers"("supplier_type");
CREATE INDEX IF NOT EXISTS "idx_suppliers_status" ON "suppliers"("status");

-- 项目表索引
CREATE INDEX IF NOT EXISTS "idx_project_headers_hid" ON "project_headers"("hid");
CREATE INDEX IF NOT EXISTS "idx_project_headers_status" ON "project_headers"("status");
CREATE INDEX IF NOT EXISTS "idx_project_headers_company_id" ON "project_headers"("company_id");

CREATE INDEX IF NOT EXISTS "idx_project_refs_header_id" ON "project_refs"("header_id");
CREATE INDEX IF NOT EXISTS "idx_project_refs_ref_number" ON "project_refs"("ref_number");
CREATE INDEX IF NOT EXISTS "idx_project_refs_status" ON "project_refs"("status");

CREATE INDEX IF NOT EXISTS "idx_project_eos_ref_id" ON "project_eos"("ref_id");
CREATE INDEX IF NOT EXISTS "idx_project_eos_eo_number" ON "project_eos"("eo_number");

-- 航班表索引
CREATE INDEX IF NOT EXISTS "idx_airport_data_iata" ON "airport_data"("airport_IATA");
CREATE INDEX IF NOT EXISTS "idx_airport_data_city" ON "airport_data"("city_name");

CREATE INDEX IF NOT EXISTS "idx_flight_orders_order_number" ON "flight_orders"("order_number");
CREATE INDEX IF NOT EXISTS "idx_flight_orders_status" ON "flight_orders"("status");
CREATE INDEX IF NOT EXISTS "idx_flight_orders_departure_date" ON "flight_orders"("departure_date");

CREATE INDEX IF NOT EXISTS "idx_passengers_order_id" ON "passengers"("order_id");
CREATE INDEX IF NOT EXISTS "idx_flight_segments_order_id" ON "flight_segments"("order_id");

-- 签证表索引
CREATE INDEX IF NOT EXISTS "idx_visa_countries_code" ON "visa_countries"("country_code");
CREATE INDEX IF NOT EXISTS "idx_visa_types_country_id" ON "visa_types"("country_id");
CREATE INDEX IF NOT EXISTS "idx_visa_projects_status" ON "visa_projects"("visa_status");

-- 旅游产品表索引
CREATE INDEX IF NOT EXISTS "idx_travelproducts_city" ON "travelproducts"("city_name");
CREATE INDEX IF NOT EXISTS "idx_travelproducts_company" ON "travelproducts"("company_name");
CREATE INDEX IF NOT EXISTS "idx_travelproducts_status" ON "travelproducts"("product_status");

-- ========================================
-- 10. 插入基础数据
-- ========================================

-- 插入默认业务类型
INSERT INTO "business_types" ("name", "description") VALUES
('机票', '航空机票服务'),
('酒店', '酒店住宿服务'),
('签证', '签证办理服务'),
('交通', '地面交通服务'),
('旅游', '旅游团服务'),
('保险', '旅游保险服务'),
('其他', '其他服务类型')
ON CONFLICT ("name") DO NOTHING;

-- 插入默认供应商类型
INSERT INTO "suppliers" ("name", "supplier_type", "status") VALUES
('默认供应商', 'other', 'active')
ON CONFLICT DO NOTHING;

-- 插入SHARE身份
INSERT INTO "visa_singapore_identity" ("identity_zh", "identity_en", "remarks") VALUES
('SHARE', 'SHARED DOCUMENTS', '共用资料')
ON CONFLICT ("identity_zh") DO NOTHING;

-- 完成提示
SELECT 'PostgreSQL 数据库模式创建完成！' as status;
"""
    
    return schema_sql

def save_schema_to_file():
    """保存模式到文件"""
    schema = generate_postgresql_schema()
    
    output_file = r"E:\DATA\20250725\postgresql_schema.sql"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(schema)
        
        print(f"✅ PostgreSQL 模式已保存到: {output_file}")
        print(f"文件大小: {len(schema)} 字符")
        print("\n下一步:")
        print("1. 在 Supabase SQL Editor 中执行此文件")
        print("2. 检查表创建是否成功")
        print("3. 准备 CSV 数据文件进行导入")
        
    except Exception as e:
        print(f"保存文件时发生错误: {e}")

if __name__ == "__main__":
    save_schema_to_file() 