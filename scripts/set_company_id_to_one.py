y#!/usr/bin/env python3
"""
将project_headers表中所有记录的company_id统一设置为1
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def set_company_id_to_one():
    """将所有project_headers记录的company_id设置为1"""
    from App.models.projects.BookingProject import ProjectHeader, CustomerCompany
    from App import create_app, db
    
    app = create_app()
    with app.app_context():
        try:
            print("=== 设置company_id为1 ===")
            
            # 检查公司ID=1是否存在
            company_one = CustomerCompany.query.get(1)
            if not company_one:
                print("❌ 错误：customer_companies表中不存在ID=1的公司")
                print("请先确保customer_companies表中有ID=1的公司记录")
                return False
            
            print(f"✅ 找到公司ID=1: {company_one.company_name}")
            
            # 统计当前数据
            total_headers = ProjectHeader.query.count()
            headers_with_company_id = ProjectHeader.query.filter(ProjectHeader.company_id.isnot(None)).count()
            headers_without_company_id = ProjectHeader.query.filter(ProjectHeader.company_id.is_(None)).count()
            
            print(f"\n当前统计:")
            print(f"  总项目数: {total_headers}")
            print(f"  已有company_id的项目: {headers_with_company_id}")
            print(f"  没有company_id的项目: {headers_without_company_id}")
            
            # 预览将要更新的数据
            headers_to_update = ProjectHeader.query.filter(
                (ProjectHeader.company_id.is_(None)) | (ProjectHeader.company_id != 1)
            ).all()
            
            print(f"\n将要更新的项目数: {len(headers_to_update)}")
            if headers_to_update:
                print("预览前10个项目:")
                for header in headers_to_update[:10]:
                    current_company = CustomerCompany.query.get(header.company_id) if header.company_id else None
                    current_company_name = current_company.company_name if current_company else "无"
                    print(f"  - HID: {header.hid}, 当前company_id: {header.company_id} ({current_company_name})")
                
                if len(headers_to_update) > 10:
                    print(f"  ... 还有 {len(headers_to_update) - 10} 个项目")
            
            # 确认操作
            confirm = input(f"\n确认将所有 {len(headers_to_update)} 个项目的company_id设置为1吗？(y/N): ")
            if confirm.lower() != 'y':
                print("❌ 操作已取消")
                return False
            
            # 执行更新
            updated_count = 0
            for header in headers_to_update:
                old_company_id = header.company_id
                header.company_id = 1
                updated_count += 1
                print(f"  更新 HID {header.hid}: company_id {old_company_id} -> 1")
            
            # 提交更改
            db.session.commit()
            print(f"\n✅ 成功更新 {updated_count} 个项目的company_id为1")
            
            # 验证结果
            final_count = ProjectHeader.query.filter_by(company_id=1).count()
            print(f"✅ 验证结果: 现在有 {final_count} 个项目的company_id为1")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 更新失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def preview_changes():
    """预览将要进行的更改（不实际执行）"""
    from App.models.projects.BookingProject import ProjectHeader, CustomerCompany
    from App import create_app
    
    app = create_app()
    with app.app_context():
        try:
            print("=== 预览更改 ===")
            
            # 检查公司ID=1是否存在
            company_one = CustomerCompany.query.get(1)
            if not company_one:
                print("❌ 错误：customer_companies表中不存在ID=1的公司")
                return False
            
            print(f"✅ 找到公司ID=1: {company_one.company_name}")
            
            # 统计当前数据
            total_headers = ProjectHeader.query.count()
            headers_with_company_id = ProjectHeader.query.filter(ProjectHeader.company_id.isnot(None)).count()
            headers_without_company_id = ProjectHeader.query.filter(ProjectHeader.company_id.is_(None)).count()
            
            print(f"\n当前统计:")
            print(f"  总项目数: {total_headers}")
            print(f"  已有company_id的项目: {headers_with_company_id}")
            print(f"  没有company_id的项目: {headers_without_company_id}")
            
            # 预览将要更新的数据
            headers_to_update = ProjectHeader.query.filter(
                (ProjectHeader.company_id.is_(None)) | (ProjectHeader.company_id != 1)
            ).all()
            
            print(f"\n将要更新的项目数: {len(headers_to_update)}")
            if headers_to_update:
                print("预览前20个项目:")
                for header in headers_to_update[:20]:
                    current_company = CustomerCompany.query.get(header.company_id) if header.company_id else None
                    current_company_name = current_company.company_name if current_company else "无"
                    print(f"  - HID: {header.hid}, 当前company_id: {header.company_id} ({current_company_name})")
                
                if len(headers_to_update) > 20:
                    print(f"  ... 还有 {len(headers_to_update) - 20} 个项目")
            
            return True
            
        except Exception as e:
            print(f"❌ 预览失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将project_headers表的company_id统一设置为1')
    parser.add_argument('--preview', action='store_true', help='只预览更改，不实际执行')
    parser.add_argument('--execute', action='store_true', help='执行更改')
    
    args = parser.parse_args()
    
    if args.preview:
        preview_changes()
    elif args.execute:
        set_company_id_to_one()
    else:
        # 默认先预览
        print("🔍 预览将要进行的更改...")
        if preview_changes():
            print("\n" + "="*50)
            confirm = input("是否执行更改？(y/N): ")
            if confirm.lower() == 'y':
                set_company_id_to_one()

if __name__ == '__main__':
    main() 