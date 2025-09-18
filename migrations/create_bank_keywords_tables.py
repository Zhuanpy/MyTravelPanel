#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建银行关键词相关表的迁移脚本
运行方式：python migrations/create_bank_keywords_tables.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.bank_keywords import BankStatementKeyword, BankKeywordCategory

def create_tables():
    """创建银行关键词相关表"""
    app = create_app()
    
    with app.app_context():
        try:
            # 创建表
            db.create_all()
            print("✅ 银行关键词表创建成功")
            
            # 验证表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'bank_statements_keywords' in tables:
                print("✅ bank_statements_keywords 表已创建")
            else:
                print("❌ bank_statements_keywords 表创建失败")
                
            if 'bank_keyword_categories' in tables:
                print("✅ bank_keyword_categories 表已创建")
            else:
                print("❌ bank_keyword_categories 表创建失败")
                
            # 插入一些示例数据
            insert_sample_data()
            
        except Exception as e:
            print(f"❌ 创建表失败: {str(e)}")
            return False
    
    return True

def insert_sample_data():
    """插入示例关键词数据"""
    try:
        # 检查是否已有数据
        if BankStatementKeyword.query.count() > 0:
            print("ℹ️  关键词表已有数据，跳过示例数据插入")
            return
            
        # UOB 示例关键词
        uob_keywords = [
            # 个人商用
            {'bank_name': 'UOB', 'keyword_type': 'personal_business', 'keyword': 'PAYNOW-FAST', 'description': 'PayNow快速支付'},
            {'bank_name': 'UOB', 'keyword_type': 'personal_business', 'keyword': 'BUS/MRT', 'description': '公共交通'},
            {'bank_name': 'UOB', 'keyword_type': 'personal_business', 'keyword': 'MIXUE', 'description': '蜜雪冰城'},
            {'bank_name': 'UOB', 'keyword_type': 'personal_business', 'keyword': 'GRAB', 'description': 'Grab打车'},
            
            # 商业
            {'bank_name': 'UOB', 'keyword_type': 'business', 'keyword': 'OFFICE RENT', 'description': '办公室租金'},
            {'bank_name': 'UOB', 'keyword_type': 'business', 'keyword': 'UTILITIES', 'description': '水电费'},
            {'bank_name': 'UOB', 'keyword_type': 'business', 'keyword': 'SUPPLIER', 'description': '供应商付款'},
            
            # 个人消费
            {'bank_name': 'UOB', 'keyword_type': 'personal', 'keyword': 'SHOPPING', 'description': '购物'},
            {'bank_name': 'UOB', 'keyword_type': 'personal', 'keyword': 'FOOD', 'description': '餐饮'},
        ]
        
        # OCBC 示例关键词
        ocbc_keywords = [
            {'bank_name': 'OCBC', 'keyword_type': 'personal_business', 'keyword': 'PAYNOW', 'description': 'PayNow支付'},
            {'bank_name': 'OCBC', 'keyword_type': 'business', 'keyword': 'RENT', 'description': '租金'},
            {'bank_name': 'OCBC', 'keyword_type': 'personal', 'keyword': 'DINING', 'description': '用餐'},
        ]
        
        # 插入数据
        all_keywords = uob_keywords + ocbc_keywords
        for kw_data in all_keywords:
            keyword = BankStatementKeyword(**kw_data)
            db.session.add(keyword)
        
        db.session.commit()
        print(f"✅ 成功插入 {len(all_keywords)} 个示例关键词")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 插入示例数据失败: {str(e)}")

if __name__ == '__main__':
    print("🚀 开始创建银行关键词表...")
    success = create_tables()
    if success:
        print("🎉 银行关键词表创建完成！")
        print("\n📋 可用的表:")
        print("  - bank_statements_keywords: 存储银行关键词")
        print("  - bank_keyword_categories: 存储关键词分类")
        print("\n🌐 访问关键词管理页面:")
        print("  http://127.0.0.1:5000/statement/keywords")
    else:
        print("💥 创建失败，请检查错误信息")
        sys.exit(1)

