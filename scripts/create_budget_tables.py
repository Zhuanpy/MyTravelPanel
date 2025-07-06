#!/usr/bin/env python3
"""
创建配套价格预算表的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader, BudgetItem

def create_budget_tables():
    """创建预算相关的数据库表"""
    app = create_app()
    
    with app.app_context():
        try:
            # 创建表
            db.create_all()
            print("✅ 预算表创建成功！")
            
            # 验证表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            tables = inspector.get_table_names()
            if 'package_budget_header' in tables:
                print("✅ package_budget_header 表已创建")
            else:
                print("❌ package_budget_header 表创建失败")
                
            if 'package_budget_items' in tables:
                print("✅ package_budget_items 表已创建")
            else:
                print("❌ package_budget_items 表创建失败")
            
            # 创建示例数据（可选）
            create_sample_data()
            
        except Exception as e:
            print(f"❌ 创建表时发生错误: {e}")
            return False
    
    return True

def create_sample_data():
    """创建示例数据"""
    try:
        # 检查是否已有数据
        if BudgetHeader.query.count() > 0:
            print("ℹ️  数据库中已有预算数据，跳过示例数据创建")
            return
        
        # 创建示例预算单
        sample_budget = BudgetHeader(
            package_name="示例套餐 - 新加坡3天2晚",
            adult_count=2,
            child_count=1,
            currency="SGD",
            status="draft",
            is_template=True,
            remarks="这是一个示例预算单，用于演示功能",
            created_by="admin"
        )
        
        db.session.add(sample_budget)
        db.session.flush()  # 获取ID
        
        # 创建示例项目
        sample_items = [
            BudgetItem(
                header_id=sample_budget.id,
                category="住宿",
                item_type="酒店",
                item_name="四星级酒店住宿",
                adult_price=150.00,
                child_price=75.00,
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=1,
                is_optional=False,
                remarks="含早餐，双人间"
            ),
            BudgetItem(
                header_id=sample_budget.id,
                category="交通",
                item_type="机票",
                item_name="往返机票",
                adult_price=300.00,
                child_price=200.00,
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=2,
                is_optional=False,
                remarks="经济舱"
            ),
            BudgetItem(
                header_id=sample_budget.id,
                category="门票",
                item_type="景点",
                item_name="环球影城门票",
                adult_price=80.00,
                child_price=60.00,
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=3,
                is_optional=True,
                remarks="可选项目"
            ),
            BudgetItem(
                header_id=sample_budget.id,
                category="餐饮",
                item_type="餐厅",
                item_name="特色餐厅晚餐",
                adult_price=50.00,
                child_price=30.00,
                count_adult_apply=True,
                count_child_apply=True,
                sort_order=4,
                is_optional=True,
                remarks="当地特色菜"
            )
        ]
        
        for item in sample_items:
            db.session.add(item)
        
        db.session.commit()
        print("✅ 示例数据创建成功！")
        print(f"   - 创建了1个预算单模板")
        print(f"   - 创建了{len(sample_items)}个预算项目")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 创建示例数据时发生错误: {e}")

def drop_budget_tables():
    """删除预算相关的数据库表（谨慎使用）"""
    app = create_app()
    
    with app.app_context():
        try:
            # 删除表
            BudgetItem.__table__.drop(db.engine, checkfirst=True)
            BudgetHeader.__table__.drop(db.engine, checkfirst=True)
            print("✅ 预算表删除成功！")
        except Exception as e:
            print(f"❌ 删除表时发生错误: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="预算表数据库迁移工具")
    parser.add_argument("--action", choices=["create", "drop"], default="create",
                       help="执行的操作：create(创建表) 或 drop(删除表)")
    
    args = parser.parse_args()
    
    if args.action == "create":
        print("🚀 开始创建预算表...")
        create_budget_tables()
    elif args.action == "drop":
        print("⚠️  开始删除预算表...")
        confirm = input("确定要删除所有预算数据吗？(y/N): ")
        if confirm.lower() == 'y':
            drop_budget_tables()
        else:
            print("操作已取消") 