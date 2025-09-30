#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为供应商表添加点击统计字段
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

def add_supplier_click_count():
    """为suppliers表添加click_count字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'suppliers' 
                AND COLUMN_NAME = 'click_count'
            """).fetchone()
            
            if result.count > 0:
                print("✅ click_count字段已存在，跳过添加")
                return
            
            # 添加click_count字段
            db.session.execute("""
                ALTER TABLE suppliers 
                ADD COLUMN click_count INT DEFAULT 0 COMMENT '点击次数'
            """)
            
            db.session.commit()
            print("✅ 成功为suppliers表添加click_count字段")
            
            # 验证字段添加成功
            result = db.session.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'suppliers' 
                AND COLUMN_NAME = 'click_count'
            """).fetchone()
            
            if result.count > 0:
                print("✅ 验证成功：click_count字段已添加到suppliers表")
            else:
                print("❌ 验证失败：click_count字段未成功添加")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 添加click_count字段失败: {e}")
            raise

if __name__ == "__main__":
    print("🚀 开始为suppliers表添加click_count字段...")
    add_supplier_click_count()
    print("🎉 供应商点击统计字段添加完成！")
