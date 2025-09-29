#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建Athina账单相关表的迁移脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

def create_athina_tables():
    """创建Athina账单相关表"""
    app = create_app()
    
    with app.app_context():
        try:
            # 导入模型以确保表定义被注册
            from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
            
            # 创建表
            db.create_all()
            
            print("✅ Athina账单表创建成功！")
            print("   - athina_booking_headers (预订头部表)")
            print("   - athina_booking_details (预订明细表)")
            
        except Exception as e:
            print(f"❌ 创建表失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_athina_tables()
