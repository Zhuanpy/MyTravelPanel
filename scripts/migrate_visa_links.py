#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行visa_links表的数据库迁移
添加visa_countries_id字段
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from sqlalchemy import text

def migrate_visa_links():
    """执行visa_links表的迁移"""
    app = create_app()
    
    with app.app_context():
        print("=== 执行visa_links表迁移 ===")
        
        try:
            # 1. 检查字段是否已存在
            print("1. 检查字段是否已存在...")
            
            # 检查visa_countries_id字段是否存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'travel_panel' 
                AND TABLE_NAME = 'visa_type_links' 
                AND COLUMN_NAME = 'visa_countries_id'
            """)).fetchone()
            
            if result:
                print("   ✓ visa_countries_id字段已存在")
                return
            
            print("   - visa_countries_id字段不存在，开始添加...")
            
            # 2. 添加新字段
            print("2. 添加visa_countries_id字段...")
            db.session.execute(text("""
                ALTER TABLE visa_type_links 
                ADD COLUMN visa_countries_id INTEGER
            """))
            print("   ✓ 字段添加成功")
            
            # 3. 添加外键约束
            print("3. 添加外键约束...")
            db.session.execute(text("""
                ALTER TABLE visa_type_links 
                ADD CONSTRAINT fk_visa_links_countries 
                FOREIGN KEY (visa_countries_id) 
                REFERENCES visa_countries(id) 
                ON DELETE CASCADE
            """))
            print("   ✓ 外键约束添加成功")
            
            # 4. 创建索引
            print("4. 创建索引...")
            db.session.execute(text("""
                CREATE INDEX idx_visa_links_countries_id 
                ON visa_type_links(visa_countries_id)
            """))
            print("   ✓ 索引创建成功")
            
            # 5. 更新现有数据
            print("5. 更新现有数据...")
            result = db.session.execute(text("""
                UPDATE visa_type_links 
                SET visa_countries_id = (
                    SELECT vt.country_id 
                    FROM visa_types vt 
                    WHERE vt.id = visa_type_links.visa_type_id
                )
                WHERE visa_countries_id IS NULL
            """))
            print(f"   ✓ 更新了 {result.rowcount} 条记录")
            
            # 6. 提交更改
            db.session.commit()
            print("   ✓ 所有更改已提交")
            
            # 7. 验证结果
            print("6. 验证结果...")
            result = db.session.execute(text("""
                SELECT 
                    vtl.id,
                    vtl.name,
                    vtl.visa_type_id,
                    vtl.visa_countries_id,
                    vc.country_name_CN as country_name
                FROM visa_type_links vtl
                LEFT JOIN visa_countries vc ON vtl.visa_countries_id = vc.id
                ORDER BY vtl.id
                LIMIT 10
            """)).fetchall()
            
            print("   前10条记录:")
            for row in result:
                print(f"   ID: {row[0]}, 名称: {row[1]}, 签证类型ID: {row[2]}, 国家ID: {row[3]}, 国家名称: {row[4]}")
            
            print("\n✅ 迁移完成！")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_visa_links() 