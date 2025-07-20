#!/usr/bin/env python3
"""
检查数据库中的签证类型
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Product.Visamodels import VisaTypes, VisaProject

def check_visa_types():
    """检查数据库中的签证类型"""
    app = create_app()
    
    with app.app_context():
        try:
            print("检查数据库中的签证类型...")
            
            # 获取所有签证类型
            visa_types = VisaTypes.query.all()
            print(f"\n数据库中的签证类型 ({len(visa_types)} 个):")
            for vt in visa_types:
                print(f"  - {vt.visa_type} (国家: {vt.country.country_name_CN if vt.country else '未知'})")
            
            # 获取所有签证项目
            visa_projects = VisaProject.query.all()
            print(f"\n签证项目中的签证类型:")
            project_types = set()
            for vp in visa_projects:
                if vp.visa_type:
                    project_types.add(vp.visa_type)
            
            for pt in sorted(project_types):
                print(f"  - {pt}")
            
            # 检查哪些项目类型在数据库中没有对应记录
            print(f"\n检查项目类型是否在数据库中有对应记录:")
            for pt in sorted(project_types):
                exists = VisaTypes.query.filter_by(visa_type=pt).first() is not None
                status = "✅" if exists else "❌"
                print(f"  {status} {pt}")
                
        except Exception as e:
            print(f"检查过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    check_visa_types() 