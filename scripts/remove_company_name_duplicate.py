#!/usr/bin/env python3
"""
移除project_headers表中的company_name字段，只保留company_id
通过外键关联获取公司名称，避免数据冗余
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_company_fields():
    """分析当前company_id和company_name字段的使用情况"""
    from App.models.projects.BookingProject import ProjectHeader, CustomerCompany
    from App import create_app, db
    
    app = create_app()
    with app.app_context():
        try:
            # 统计信息
            total_headers = ProjectHeader.query.count()
            headers_with_company_id = ProjectHeader.query.filter(ProjectHeader.company_id.isnot(None)).count()
            headers_with_company_name = ProjectHeader.query.filter(ProjectHeader.company_name.isnot(None)).count()
            
            print("=== 当前字段使用情况分析 ===")
            print(f"总项目数: {total_headers}")
            print(f"有company_id的项目: {headers_with_company_id}")
            print(f"有company_name的项目: {headers_with_company_name}")
            
            # 检查数据一致性
            inconsistent_data = []
            headers = ProjectHeader.query.all()
            
            for header in headers:
                if header.company_id:
                    # 查找对应的公司
                    company = CustomerCompany.query.get(header.company_id)
                    if company and header.company_name != company.company_name:
                        inconsistent_data.append({
                            'header_id': header.id,
                            'header_hid': header.hid,
                            'company_id': header.company_id,
                            'stored_name': header.company_name,
                            'actual_name': company.company_name
                        })
            
            print(f"\n数据不一致的项目数: {len(inconsistent_data)}")
            if inconsistent_data:
                print("\n不一致的数据示例:")
                for item in inconsistent_data[:5]:  # 只显示前5个
                    print(f"  - HID: {item['header_hid']}, 存储名称: {item['stored_name']}, 实际名称: {item['actual_name']}")
            
            return {
                'total': total_headers,
                'with_company_id': headers_with_company_id,
                'with_company_name': headers_with_company_name,
                'inconsistent': len(inconsistent_data)
            }
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None

def migrate_company_data():
    """迁移公司数据：确保company_id正确，移除company_name字段"""
    from App.models.projects.BookingProject import ProjectHeader, CustomerCompany
    from App import create_app, db
    
    app = create_app()
    with app.app_context():
        try:
            print("\n=== 开始迁移公司数据 ===")
            
            # 1. 更新company_name字段，使其与company_id一致
            headers = ProjectHeader.query.all()
            updated_count = 0
            
            for header in headers:
                if header.company_id:
                    company = CustomerCompany.query.get(header.company_id)
                    if company and header.company_name != company.company_name:
                        header.company_name = company.company_name
                        updated_count += 1
                        print(f"  更新 HID {header.hid}: {header.company_name} -> {company.company_name}")
            
            if updated_count > 0:
                db.session.commit()
                print(f"✅ 更新了 {updated_count} 条记录的公司名称")
            
            # 2. 为没有company_id但有company_name的记录创建或关联公司
            headers_without_company_id = ProjectHeader.query.filter(
                ProjectHeader.company_id.is_(None),
                ProjectHeader.company_name.isnot(None)
            ).all()
            
            linked_count = 0
            for header in headers_without_company_id:
                if header.company_name:
                    # 查找是否已存在该公司
                    company = CustomerCompany.query.filter_by(company_name=header.company_name).first()
                    if company:
                        header.company_id = company.id
                        linked_count += 1
                        print(f"  关联 HID {header.hid} 到公司: {company.company_name}")
                    else:
                        print(f"  ⚠️  HID {header.hid} 的公司 '{header.company_name}' 不存在，需要手动处理")
            
            if linked_count > 0:
                db.session.commit()
                print(f"✅ 关联了 {linked_count} 条记录到现有公司")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def create_migration_sql():
    """生成数据库迁移SQL"""
    sql_content = """
-- 迁移脚本：移除project_headers表中的company_name字段
-- 执行前请确保所有数据已正确关联到company_id

-- 1. 备份company_name数据（可选）
-- CREATE TABLE project_headers_backup AS SELECT * FROM project_headers;

-- 2. 确保所有记录都有正确的company_id
-- 这一步需要手动检查，确保没有孤立的数据

-- 3. 删除company_name字段
ALTER TABLE project_headers DROP COLUMN company_name;

-- 4. 验证外键约束
-- 确保company_id的外键约束正常工作
"""
    
    with open('scripts/migrate_remove_company_name.sql', 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print("✅ 已生成迁移SQL文件: scripts/migrate_remove_company_name.sql")

def update_code_files():
    """更新相关代码文件，移除对company_name字段的引用"""
    print("\n=== 需要更新的代码文件 ===")
    print("以下文件需要手动更新，移除对company_name字段的引用：")
    print("1. App/models/projects/BookingProject.py - ProjectHeader模型")
    print("2. App/forms/header_forms.py - 移除company_name字段")
    print("3. App/templates/projects/BookingProject/create_header.html - 移除company_name输入框")
    print("4. App/routes/projects/BookingProject/project.py - 更新创建和编辑逻辑")
    print("5. 其他使用header.company_name的模板文件")
    
    print("\n=== 建议的修改步骤 ===")
    print("1. 在ProjectHeader模型中添加关联关系：")
    print("   company = db.relationship('CustomerCompany', backref='headers')")
    print("2. 在模板中使用：header.company.company_name")
    print("3. 在路由中确保传递company对象到模板")
    print("4. 移除表单中的company_name字段")

def main():
    """主函数"""
    print("🔍 分析project_headers表中的company字段使用情况...")
    
    # 1. 分析当前情况
    stats = analyze_company_fields()
    if not stats:
        return
    
    # 2. 询问是否继续
    print(f"\n发现 {stats['inconsistent']} 条数据不一致")
    confirm = input("是否继续迁移数据？(y/N): ")
    if confirm.lower() != 'y':
        print("❌ 操作已取消")
        return
    
    # 3. 迁移数据
    if migrate_company_data():
        print("\n✅ 数据迁移完成")
        
        # 4. 生成SQL迁移脚本
        create_migration_sql()
        
        # 5. 提示代码更新
        update_code_files()
        
        print("\n🎯 下一步操作：")
        print("1. 检查迁移结果")
        print("2. 执行SQL迁移脚本删除company_name字段")
        print("3. 更新相关代码文件")
        print("4. 测试系统功能")
    else:
        print("❌ 数据迁移失败")

if __name__ == '__main__':
    main() 