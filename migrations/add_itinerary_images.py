#!/usr/bin/env python3
"""
添加行程图片字段的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

def add_itinerary_image_columns():
    """为 tour_itinerary 表添加图片字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 添加 image1 字段
            db.engine.execute(text("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image1 VARCHAR(500) NULL COMMENT '图片1路径'
            """))
            print("✓ 成功添加 image1 字段")
            
            # 添加 image2 字段
            db.engine.execute(text("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image2 VARCHAR(500) NULL COMMENT '图片2路径'
            """))
            print("✓ 成功添加 image2 字段")
            
            # 添加 image3 字段
            db.engine.execute(text("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image3 VARCHAR(500) NULL COMMENT '图片3路径'
            """))
            print("✓ 成功添加 image3 字段")
            
            print("✅ 所有图片字段添加完成！")
            
        except Exception as e:
            print(f"❌ 添加字段时发生错误: {str(e)}")
            # 检查字段是否已存在
            try:
                result = db.engine.execute(text("SHOW COLUMNS FROM tour_itinerary LIKE 'image1'"))
                if result.fetchone():
                    print("ℹ️  image1 字段已存在")
                else:
                    print("ℹ️  image1 字段不存在")
            except:
                pass

if __name__ == "__main__":
    add_itinerary_image_columns()
