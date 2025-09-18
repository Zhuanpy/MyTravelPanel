#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库表结构
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_database():
    """修复数据库表结构"""
    try:
        from App_new import create_app
        from App_new.exts import db
        from App_new.finance.models.bank_keywords import BankStatementKeyword, BankKeywordCategory
        
        app = create_app()
        
        with app.app_context():
            print("检查数据库表结构...")
            
            # 检查表是否存在
            result = db.session.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='bank_statements_keywords'
            """).fetchone()
            
            if result:
                print("✅ bank_statements_keywords 表存在")
                
                # 检查表结构
                result = db.session.execute("PRAGMA table_info(bank_statements_keywords)").fetchall()
                print("当前表结构:")
                for row in result:
                    print(f"  {row[1]} ({row[2]})")
                
                # 删除旧表（如果字段名有问题）
                if any(' ' in row[1] for row in result):
                    print("发现字段名有空格，重新创建表...")
                    db.drop_all()
                    db.create_all()
                    print("✅ 表结构已重新创建")
                else:
                    print("✅ 表结构正确")
            else:
                print("❌ 表不存在，创建新表...")
                db.create_all()
                print("✅ 表已创建")
            
            # 测试插入数据
            print("测试插入数据...")
            test_keyword = BankStatementKeyword(
                bank_name='OCBC',
                keyword_type='business',
                keyword='TEST_KEYWORD',
                description='测试关键词',
                is_active=True
            )
            
            db.session.add(test_keyword)
            db.session.commit()
            print("✅ 测试数据插入成功")
            
            # 清理测试数据
            db.session.delete(test_keyword)
            db.session.commit()
            print("✅ 测试数据已清理")
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_database()

