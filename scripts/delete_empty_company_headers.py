#!/usr/bin/env python3
"""
删除project_headers表中company_id为空的数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def delete_empty_company_headers():
    """删除project_headers表中company_id为空的数据"""
    from App.models.projects.BookingProject import ProjectHeader
    from App import create_app, db
    
    app = create_app()
    with app.app_context():
        try:
            # 查询company_id为空的数据
            empty_company_headers = ProjectHeader.query.filter(
                (ProjectHeader.company_id.is_(None)) | (ProjectHeader.company_id == 0)
            ).all()
            
            print(f"找到 {len(empty_company_headers)} 条company_id为空的数据:")
            
            if empty_company_headers:
                for header in empty_company_headers:
                    print(f"  - ID: {header.id}, HID: {header.hid}, 描述: {header.desc}, 公司: {header.company_name}")
                
                # 确认删除
                confirm = input(f"\n确认删除这 {len(empty_company_headers)} 条数据吗？(y/N): ")
                
                if confirm.lower() == 'y':
                    # 删除数据
                    for header in empty_company_headers:
                        db.session.delete(header)
                    
                    # 提交事务
                    db.session.commit()
                    print(f"✅ 成功删除 {len(empty_company_headers)} 条数据")
                else:
                    print("❌ 操作已取消")
            else:
                print("✅ 没有找到company_id为空的数据")
            
            # 显示剩余数据统计
            total_headers = ProjectHeader.query.count()
            print(f"\n当前project_headers表总记录数: {total_headers}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 删除失败: {e}")
            import traceback
            traceback.print_exc()

def preview_empty_company_headers():
    """预览company_id为空的数据（不删除）"""
    from App.models.projects.BookingProject import ProjectHeader
    from App import create_app
    
    app = create_app()
    with app.app_context():
        try:
            # 查询company_id为空的数据
            empty_company_headers = ProjectHeader.query.filter(
                (ProjectHeader.company_id.is_(None)) | (ProjectHeader.company_id == 0)
            ).all()
            
            print(f"预览 - 找到 {len(empty_company_headers)} 条company_id为空的数据:")
            
            if empty_company_headers:
                for header in empty_company_headers:
                    print(f"  - ID: {header.id}, HID: {header.hid}, 描述: {header.desc}, 公司: {header.company_name}")
            else:
                print("✅ 没有找到company_id为空的数据")
            
            # 显示统计信息
            total_headers = ProjectHeader.query.count()
            empty_count = len(empty_company_headers)
            print(f"\n统计信息:")
            print(f"  总记录数: {total_headers}")
            print(f"  company_id为空: {empty_count}")
            print(f"  company_id不为空: {total_headers - empty_count}")
            
        except Exception as e:
            print(f"❌ 预览失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='删除project_headers表中company_id为空的数据')
    parser.add_argument('--preview', action='store_true', help='仅预览，不删除')
    parser.add_argument('--delete', action='store_true', help='执行删除操作')
    
    args = parser.parse_args()
    
    if args.preview:
        print("=== 预览模式 ===")
        preview_empty_company_headers()
    elif args.delete:
        print("=== 删除模式 ===")
        delete_empty_company_headers()
    else:
        print("请指定操作模式:")
        print("  --preview  预览company_id为空的数据")
        print("  --delete   删除company_id为空的数据")
        print("\n示例:")
        print("  python scripts/delete_empty_company_headers.py --preview")
        print("  python scripts/delete_empty_company_headers.py --delete") 