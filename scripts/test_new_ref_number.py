#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的REF编号生成逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef

def test_new_ref_number():
    """测试新的REF编号生成逻辑"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试新的REF编号生成逻辑 ===")
        
        # 1. 查看现有的REF编号
        existing_refs = ProjectRef.query.all()
        print(f"数据库中现有 {len(existing_refs)} 个REF")
        
        if existing_refs:
            print("现有REF编号:")
            for ref in existing_refs:
                print(f"  {ref.ref_number}")
        
        # 2. 测试生成新的REF编号
        print(f"\n测试生成新的REF编号:")
        for i in range(5):
            new_ref_number = ProjectRef.generate_ref_number()
            print(f"  第{i+1}个: {new_ref_number}")
        
        # 3. 测试数据库查询逻辑
        print(f"\n测试数据库查询逻辑:")
        
        # 查找所有以'R'开头的REF编号
        r_refs = ProjectRef.query.filter(
            ProjectRef.ref_number.like('R%')
        ).order_by(ProjectRef.ref_number).all()
        
        print(f"以'R'开头的REF编号:")
        for ref in r_refs:
            print(f"  {ref.ref_number}")
        
        # 4. 测试数字排序逻辑
        print(f"\n测试数字排序逻辑:")
        try:
            # 使用数据库函数排序
            sorted_refs = ProjectRef.query.filter(
                ProjectRef.ref_number.like('R%')
            ).order_by(
                db.func.cast(db.func.substring(ProjectRef.ref_number, 2), db.Integer).desc()
            ).all()
            
            print("按数字排序的REF编号（降序）:")
            for ref in sorted_refs:
                print(f"  {ref.ref_number}")
                
            if sorted_refs:
                print(f"最大编号: {sorted_refs[0].ref_number}")
        except Exception as e:
            print(f"排序查询出错: {e}")
        
        print(f"\n✅ 测试完成")

if __name__ == "__main__":
    test_new_ref_number() 