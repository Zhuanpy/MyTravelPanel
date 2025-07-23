#!/usr/bin/env python3
"""
更新accounts表的website_url字段长度从500到2000
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def update_website_url_length():
    """更新website_url字段长度"""
    app = create_app()
    
    with app.app_context():
        try:
            # 执行ALTER TABLE语句
            sql = "ALTER TABLE accounts MODIFY COLUMN website_url VARCHAR(2000)"
            db.session.execute(sql)
            db.session.commit()
            
            print("✅ 成功更新website_url字段长度为2000")
            
            # 验证更新
            result = db.session.execute("SHOW COLUMNS FROM accounts LIKE 'website_url'")
            column_info = result.fetchone()
            if column_info:
                print(f"✅ 验证成功: website_url字段类型为 {column_info[1]}")
            else:
                print("❌ 验证失败: 未找到website_url字段")
                
        except Exception as e:
            print(f"❌ 更新失败: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    update_website_url_length() 