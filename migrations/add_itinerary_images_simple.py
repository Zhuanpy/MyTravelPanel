#!/usr/bin/env python3
"""
添加行程图片字段的数据库迁移脚本（简化版）
"""

import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def add_itinerary_image_columns():
    """为 tour_itinerary 表添加图片字段"""
    
    # 数据库连接配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'travel_panel_new'),
        'charset': 'utf8mb4'
    }
    
    try:
        # 连接数据库
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        print("🔗 已连接到数据库")
        
        # 检查字段是否已存在
        cursor.execute("SHOW COLUMNS FROM tour_itinerary LIKE 'image1'")
        if cursor.fetchone():
            print("ℹ️  image1 字段已存在，跳过")
        else:
            # 添加 image1 字段
            cursor.execute("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image1 VARCHAR(500) NULL COMMENT '图片1路径'
            """)
            print("✓ 成功添加 image1 字段")
        
        cursor.execute("SHOW COLUMNS FROM tour_itinerary LIKE 'image2'")
        if cursor.fetchone():
            print("ℹ️  image2 字段已存在，跳过")
        else:
            # 添加 image2 字段
            cursor.execute("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image2 VARCHAR(500) NULL COMMENT '图片2路径'
            """)
            print("✓ 成功添加 image2 字段")
        
        cursor.execute("SHOW COLUMNS FROM tour_itinerary LIKE 'image3'")
        if cursor.fetchone():
            print("ℹ️  image3 字段已存在，跳过")
        else:
            # 添加 image3 字段
            cursor.execute("""
                ALTER TABLE tour_itinerary 
                ADD COLUMN image3 VARCHAR(500) NULL COMMENT '图片3路径'
            """)
            print("✓ 成功添加 image3 字段")
        
        # 提交更改
        connection.commit()
        print("✅ 所有图片字段添加完成！")
        
    except Exception as e:
        print(f"❌ 添加字段时发生错误: {str(e)}")
        if 'connection' in locals():
            connection.rollback()
    finally:
        if 'connection' in locals():
            connection.close()
            print("🔌 数据库连接已关闭")

if __name__ == "__main__":
    add_itinerary_image_columns()
