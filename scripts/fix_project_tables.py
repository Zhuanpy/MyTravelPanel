#!/usr/bin/env python3
"""
修复项目相关数据库表结构的脚本
"""

import sys
import os
import pymysql
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App.config import Config

def get_database_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def check_table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
    """, (Config.DB_NAME, table_name))
    result = cursor.fetchone()
    return result['count'] > 0

def check_column_exists(cursor, table_name, column_name):
    """检查字段是否存在"""
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
    """, (Config.DB_NAME, table_name, column_name))
    result = cursor.fetchone()
    return result['count'] > 0

def create_customer_companies_table(cursor):
    """创建客户公司表"""
    if not check_table_exists(cursor, 'customer_companies'):
        print("创建客户公司表...")
        cursor.execute("""
            CREATE TABLE `customer_companies` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `company_name` varchar(100) NOT NULL COMMENT '公司名称',
                `company_code` varchar(50) DEFAULT NULL COMMENT '公司代码',
                `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
                `contact_phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
                `contact_email` varchar(100) DEFAULT NULL COMMENT '联系邮箱',
                `address` text DEFAULT NULL COMMENT '公司地址',
                `industry` varchar(50) DEFAULT NULL COMMENT '行业',
                `company_size` varchar(20) DEFAULT NULL COMMENT '公司规模',
                `credit_limit` decimal(15,2) DEFAULT NULL COMMENT '信用额度',
                `currency` varchar(10) DEFAULT 'SGD' COMMENT '币种',
                `status` enum('active','inactive','suspended') DEFAULT 'active' COMMENT '状态',
                `remarks` text DEFAULT NULL COMMENT '备注',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_company_name` (`company_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户公司表'
        """)
        print("客户公司表创建成功")
    else:
        print("客户公司表已存在")

def create_customers_table(cursor):
    """创建客户表"""
    if not check_table_exists(cursor, 'customers'):
        print("创建客户表...")
        cursor.execute("""
            CREATE TABLE `customers` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `name` varchar(100) NOT NULL COMMENT '客户名称',
                `phone` varchar(20) DEFAULT NULL COMMENT '电话',
                `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
                `id_number` varchar(30) DEFAULT NULL COMMENT '证件号码',
                `id_type` varchar(20) DEFAULT NULL COMMENT '证件类型',
                `address` text DEFAULT NULL COMMENT '地址',
                `company` varchar(100) DEFAULT NULL COMMENT '公司名称',
                `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户表'
        """)
        print("客户表创建成功")
    else:
        print("客户表已存在")

def create_project_headers_table(cursor):
    """创建项目主表"""
    if not check_table_exists(cursor, 'project_headers'):
        print("创建项目主表...")
        cursor.execute("""
            CREATE TABLE `project_headers` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `hid` varchar(20) NOT NULL COMMENT '项目编号（如H20240702001）',
                `desc` varchar(200) DEFAULT NULL COMMENT '项目描述',
                `company_id` int(11) DEFAULT NULL COMMENT '客户公司ID',
                `company_name` varchar(100) DEFAULT NULL COMMENT '公司名称',
                `limit` varchar(50) DEFAULT NULL COMMENT '额度限制',
                `contact` varchar(50) DEFAULT NULL COMMENT '联系人',
                `dept` varchar(50) DEFAULT NULL COMMENT '部门',
                `staff_id` int(11) DEFAULT NULL COMMENT '经办人ID',
                `staff_name` varchar(50) DEFAULT NULL COMMENT '经办人姓名',
                `currency` varchar(10) DEFAULT NULL COMMENT '币种',
                `type` varchar(50) DEFAULT NULL COMMENT '类型',
                `source` varchar(50) DEFAULT NULL COMMENT '来源',
                `country` varchar(50) DEFAULT NULL COMMENT '国家',
                `status` enum('draft','active','completed','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
                `last_updated_by` varchar(50) DEFAULT NULL COMMENT '最后操作人',
                `remarks` text DEFAULT NULL COMMENT '备注',
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_hid` (`hid`),
                KEY `idx_company_id` (`company_id`),
                KEY `idx_status` (`status`),
                KEY `idx_created_at` (`created_at`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目主表'
        """)
        print("项目主表创建成功")
    else:
        print("项目主表已存在")

def create_project_refs_table(cursor):
    """创建项目REF表"""
    if not check_table_exists(cursor, 'project_refs'):
        print("创建项目REF表...")
        cursor.execute("""
            CREATE TABLE `project_refs` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `header_id` int(11) NOT NULL COMMENT 'HID主表ID',
                `ref_number` varchar(30) NOT NULL COMMENT 'REF编号',
                `name` varchar(100) DEFAULT NULL COMMENT 'REF订单名称',
                `ref_type_id` int(11) NOT NULL COMMENT 'REF类型ID',
                `description` varchar(200) NOT NULL COMMENT '描述',
                `supplier_id` int(11) DEFAULT NULL COMMENT '供应商ID',
                `supplier_contact` varchar(50) DEFAULT NULL COMMENT '供应商联系人',
                `supplier_phone` varchar(20) DEFAULT NULL COMMENT '供应商联系电话',
                `selling_price` decimal(10,2) DEFAULT NULL COMMENT '销售价格',
                `cost_price` decimal(10,2) DEFAULT NULL COMMENT '成本价格',
                `currency` varchar(3) NOT NULL DEFAULT 'SGD' COMMENT '货币类型',
                `expected_delivery_date` date DEFAULT NULL COMMENT '预计交付日期',
                `actual_delivery_date` date DEFAULT NULL COMMENT '实际交付日期',
                `remarks` text DEFAULT NULL COMMENT '备注',
                `attachments` text DEFAULT NULL COMMENT '附件列表(JSON)',
                `status` enum('draft','processing','completed','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
                `payment_status` enum('unpaid','partial','paid','refunded') NOT NULL DEFAULT 'unpaid' COMMENT '支付状态',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_ref_number` (`ref_number`),
                KEY `idx_header_id` (`header_id`),
                KEY `idx_ref_type_id` (`ref_type_id`),
                KEY `idx_supplier_id` (`supplier_id`),
                KEY `idx_status` (`status`),
                KEY `idx_payment_status` (`payment_status`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目REF表'
        """)
        print("项目REF表创建成功")
    else:
        print("项目REF表已存在")
        # 检查是否缺少header_id字段
        if not check_column_exists(cursor, 'project_refs', 'header_id'):
            print("添加缺失的header_id字段...")
            cursor.execute("""
                ALTER TABLE `project_refs` 
                ADD COLUMN `header_id` int(11) NOT NULL COMMENT 'HID主表ID' AFTER `id`
            """)
            print("header_id字段添加成功")

def create_project_eos_table(cursor):
    """创建项目EO表"""
    if not check_table_exists(cursor, 'project_eos'):
        print("创建项目EO表...")
        cursor.execute("""
            CREATE TABLE `project_eos` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ref_id` int(11) NOT NULL COMMENT 'REF明细ID',
                `eo_number` varchar(30) NOT NULL COMMENT 'EO编号',
                `name` varchar(100) DEFAULT NULL COMMENT 'EO订单名称',
                `supplier_type` enum('visa','flight','hotel','transport','local_operator','other') NOT NULL COMMENT '供应商类型',
                `supplier_id` int(11) NOT NULL COMMENT '供应商ID',
                `external_system` varchar(50) DEFAULT NULL COMMENT '外部系统名称',
                `external_status` varchar(50) DEFAULT NULL COMMENT '外部系统状态',
                `external_reference` varchar(100) DEFAULT NULL COMMENT '外部系统参考号',
                `amount` decimal(10,2) NOT NULL COMMENT '金额',
                `currency` varchar(3) NOT NULL DEFAULT 'SGD' COMMENT '货币类型',
                `remarks` text DEFAULT NULL COMMENT '备注',
                `status` enum('draft','confirmed','paid','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uk_eo_number` (`eo_number`),
                KEY `idx_ref_id` (`ref_id`),
                KEY `idx_supplier_id` (`supplier_id`),
                KEY `idx_supplier_type` (`supplier_type`),
                KEY `idx_status` (`status`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目EO表'
        """)
        print("项目EO表创建成功")
    else:
        print("项目EO表已存在")

def create_ref_order_items_table(cursor):
    """创建REF订单项目表"""
    if not check_table_exists(cursor, 'ref_order_items'):
        print("创建REF订单项目表...")
        cursor.execute("""
            CREATE TABLE `ref_order_items` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `ref_id` int(11) NOT NULL COMMENT 'REF ID',
                `item_name` varchar(200) NOT NULL COMMENT '项目名称',
                `quantity` int(11) NOT NULL DEFAULT 1 COMMENT '数量',
                `unit_price` decimal(10,2) NOT NULL COMMENT '单价',
                `total_price` decimal(10,2) NOT NULL COMMENT '总价',
                `remarks` text DEFAULT NULL COMMENT '备注',
                `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                KEY `idx_ref_id` (`ref_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='REF订单项目表'
        """)
        print("REF订单项目表创建成功")
    else:
        print("REF订单项目表已存在")

def add_foreign_key_constraints(cursor):
    """添加外键约束"""
    print("检查并添加外键约束...")
    
    # 检查project_headers表的company_id外键
    if check_table_exists(cursor, 'customer_companies'):
        try:
            cursor.execute("""
                ALTER TABLE `project_headers` 
                ADD CONSTRAINT `fk_project_headers_company` 
                FOREIGN KEY (`company_id`) REFERENCES `customer_companies` (`id`) ON DELETE SET NULL
            """)
            print("project_headers.company_id外键约束添加成功")
        except Exception as e:
            if "Duplicate key name" not in str(e):
                print(f"添加project_headers.company_id外键约束失败: {e}")
    
    # 检查project_refs表的header_id外键
    if check_table_exists(cursor, 'project_headers'):
        try:
            cursor.execute("""
                ALTER TABLE `project_refs` 
                ADD CONSTRAINT `fk_project_refs_header` 
                FOREIGN KEY (`header_id`) REFERENCES `project_headers` (`id`) ON DELETE CASCADE
            """)
            print("project_refs.header_id外键约束添加成功")
        except Exception as e:
            if "Duplicate key name" not in str(e):
                print(f"添加project_refs.header_id外键约束失败: {e}")
    
    # 检查project_eos表的ref_id外键
    if check_table_exists(cursor, 'project_refs'):
        try:
            cursor.execute("""
                ALTER TABLE `project_eos` 
                ADD CONSTRAINT `fk_project_eos_ref` 
                FOREIGN KEY (`ref_id`) REFERENCES `project_refs` (`id`) ON DELETE CASCADE
            """)
            print("project_eos.ref_id外键约束添加成功")
        except Exception as e:
            if "Duplicate key name" not in str(e):
                print(f"添加project_eos.ref_id外键约束失败: {e}")

def main():
    """主函数"""
    print("开始修复项目相关数据库表结构...")
    
    connection = get_database_connection()
    if not connection:
        print("无法连接到数据库，请检查配置")
        return
    
    try:
        with connection.cursor() as cursor:
            # 创建所有必要的表
            create_customer_companies_table(cursor)
            create_customers_table(cursor)
            create_project_headers_table(cursor)
            create_project_refs_table(cursor)
            create_project_eos_table(cursor)
            create_ref_order_items_table(cursor)
            
            # 添加外键约束
            add_foreign_key_constraints(cursor)
            
            # 提交更改
            connection.commit()
            print("\n数据库表结构修复完成！")
            
    except Exception as e:
        print(f"修复过程中出现错误: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    main() 