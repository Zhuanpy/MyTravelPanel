#!/usr/bin/env python3
"""
执行删除project_headers表中company_name字段的SQL脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def execute_drop_company_name():
    """执行删除company_name字段的SQL"""
    from App import create_app, db
    
    app = create_app()
    with app.app_context():
        try:
            print("=== 执行删除company_name字段 ===")
            
            # 检查当前表结构
            result = db.session.execute("DESCRIBE project_headers")
            columns = [row[0] for row in result]
            print(f"当前表字段: {columns}")
            
            if 'company_name' not in columns:
                print("✅ company_name字段已不存在，无需删除")
                return True
            
            # 确认操作
            confirm = input("确认删除company_name字段吗？(y/N): ")
            if confirm.lower() != 'y':
                print("❌ 操作已取消")
                return False
            
            # 执行删除
            print("正在删除company_name字段...")
            db.session.execute("ALTER TABLE project_headers DROP COLUMN company_name")
            db.session.commit()
            
            print("✅ company_name字段删除成功")
            
            # 验证删除结果
            result = db.session.execute("DESCRIBE project_headers")
            columns = [row[0] for row in result]
            print(f"删除后表字段: {columns}")
            
            if 'company_name' not in columns:
                print("✅ 验证成功：company_name字段已删除")
            else:
                print("❌ 验证失败：company_name字段仍然存在")
                return False
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 删除失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """主函数"""
    print("🔧 准备删除project_headers表中的company_name字段...")
    
    if execute_drop_company_name():
        print("\n✅ 字段删除完成")
        print("\n🎯 下一步操作：")
        print("1. 重启应用服务器")
        print("2. 测试项目创建和编辑功能")
        print("3. 验证公司信息显示正常")
    else:
        print("❌ 字段删除失败")

if __name__ == '__main__':
    main() 