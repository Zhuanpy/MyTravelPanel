#!/usr/bin/env python3
"""
为visa_projects表添加header_id和ref_id字段的迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db

def add_visa_project_links_fields():
    """为visa_projects表添加header_id和ref_id字段"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始为visa_projects表添加header_id和ref_id字段...")
            
            # 检查字段是否已存在
            with db.engine.connect() as conn:
                # 检查header_id字段
                result = conn.execute(db.text("SHOW COLUMNS FROM visa_projects LIKE 'header_id'"))
                header_id_exists = result.fetchone() is not None
                
                # 检查ref_id字段
                result = conn.execute(db.text("SHOW COLUMNS FROM visa_projects LIKE 'ref_id'"))
                ref_id_exists = result.fetchone() is not None
                
                print(f"header_id字段存在: {header_id_exists}")
                print(f"ref_id字段存在: {ref_id_exists}")
                
                # 添加header_id字段
                if not header_id_exists:
                    print("添加header_id字段...")
                    conn.execute(db.text("""
                        ALTER TABLE visa_projects 
                        ADD COLUMN header_id INT NULL,
                        ADD CONSTRAINT fk_visa_projects_header 
                        FOREIGN KEY (header_id) REFERENCES project_headers(id)
                    """))
                    print("✅ header_id字段添加成功")
                else:
                    print("⚠️ header_id字段已存在")
                
                # 添加ref_id字段
                if not ref_id_exists:
                    print("添加ref_id字段...")
                    conn.execute(db.text("""
                        ALTER TABLE visa_projects 
                        ADD COLUMN ref_id INT NULL,
                        ADD CONSTRAINT fk_visa_projects_ref 
                        FOREIGN KEY (ref_id) REFERENCES project_refs(id)
                    """))
                    print("✅ ref_id字段添加成功")
                else:
                    print("⚠️ ref_id字段已存在")
                
                # 提交事务
                conn.commit()
            
            print("\n数据库迁移完成！")
            
            # 验证字段是否添加成功
            print("\n=== 验证字段添加结果 ===")
            with db.engine.connect() as conn:
                result = conn.execute(db.text("DESCRIBE visa_projects"))
                columns = result.fetchall()
                
                print("visa_projects表结构:")
                for column in columns:
                    if 'header_id' in column or 'ref_id' in column:
                        print(f"  {column[0]}: {column[1]} {column[2]} {column[3]} {column[4]} {column[5]}")
                
            print("\n迁移脚本执行完成！")
                
        except Exception as e:
            print(f"迁移过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    add_visa_project_links_fields() 