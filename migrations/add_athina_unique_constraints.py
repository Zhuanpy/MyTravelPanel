# -*- coding: utf-8 -*-
"""
为Athina表添加唯一约束的迁移脚本
- athina_booking_headers.booking_header_id 已有唯一约束
- athina_booking_details.booking_ref 添加唯一约束
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """执行数据库迁移"""
    
    # 数据库文件路径
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'travel_panel_new.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("开始执行Athina表唯一约束迁移...")
        
        # 1. 检查athina_booking_details表是否存在booking_ref重复数据
        print("检查athina_booking_details表中的重复booking_ref...")
        cursor.execute("""
            SELECT booking_ref, COUNT(*) as count 
            FROM athina_booking_details 
            WHERE booking_ref IS NOT NULL AND booking_ref != ''
            GROUP BY booking_ref 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"发现 {len(duplicates)} 个重复的booking_ref:")
            for booking_ref, count in duplicates:
                print(f"  - {booking_ref}: {count} 条记录")
            
            # 删除重复记录，保留最新的记录
            print("删除重复记录，保留最新的记录...")
            for booking_ref, count in duplicates:
                cursor.execute("""
                    DELETE FROM athina_booking_details 
                    WHERE booking_ref = ? AND id NOT IN (
                        SELECT id FROM athina_booking_details 
                        WHERE booking_ref = ? 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    )
                """, (booking_ref, booking_ref))
                print(f"  删除 {booking_ref} 的重复记录")
        
        # 2. 为booking_ref字段添加唯一约束
        print("为athina_booking_details.booking_ref添加唯一约束...")
        
        # 首先检查约束是否已存在
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='athina_booking_details'
        """)
        
        table_sql = cursor.fetchone()
        if table_sql and 'UNIQUE' not in table_sql[0]:
            # 创建新表结构
            print("重新创建athina_booking_details表以添加唯一约束...")
            
            # 创建新表
            cursor.execute("""
                CREATE TABLE athina_booking_details_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    header_id INTEGER NOT NULL,
                    corporate_name VARCHAR(200),
                    client_name VARCHAR(200),
                    booking_ref VARCHAR(100) UNIQUE,
                    book_type VARCHAR(50),
                    book_date DATE,
                    dep_date DATE,
                    itin_desc TEXT,
                    gross_curr VARCHAR(10),
                    gross_amount NUMERIC(15, 2),
                    gross_tax NUMERIC(15, 2),
                    discount NUMERIC(15, 2),
                    local_gross NUMERIC(15, 2),
                    local_cost NUMERIC(15, 2),
                    profit_loss NUMERIC(15, 2),
                    margin NUMERIC(5, 2),
                    balance NUMERIC(15, 2),
                    supplier VARCHAR(200),
                    consultant VARCHAR(200),
                    sales_consultant VARCHAR(200),
                    invoice_no VARCHAR(100),
                    invoice_date DATE,
                    is_subtotal BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (header_id) REFERENCES athina_booking_headers (id)
                )
            """)
            
            # 复制数据到新表
            cursor.execute("""
                INSERT INTO athina_booking_details_new 
                SELECT * FROM athina_booking_details
            """)
            
            # 删除旧表
            cursor.execute("DROP TABLE athina_booking_details")
            
            # 重命名新表
            cursor.execute("ALTER TABLE athina_booking_details_new RENAME TO athina_booking_details")
            
            print("athina_booking_details表结构更新完成")
        else:
            print("athina_booking_details表已包含唯一约束")
        
        # 3. 验证约束是否生效
        print("验证唯一约束...")
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='athina_booking_details'
        """)
        
        updated_table_sql = cursor.fetchone()
        if updated_table_sql and 'UNIQUE' in updated_table_sql[0]:
            print("✅ athina_booking_details.booking_ref唯一约束添加成功")
        else:
            print("❌ athina_booking_details.booking_ref唯一约束添加失败")
        
        # 提交更改
        conn.commit()
        print("✅ Athina表唯一约束迁移完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移过程中发生错误: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"开始执行Athina数据库迁移 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = migrate_database()
    if success:
        print("🎉 迁移成功完成")
    else:
        print("💥 迁移失败")
