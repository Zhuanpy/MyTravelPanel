#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试删除项目header功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef, ProjectEO

def test_delete_header():
    """测试删除header功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试删除项目Header功能 ===")
        
        # 1. 查看当前有多少个项目
        headers = ProjectHeader.query.all()
        print(f"当前共有 {len(headers)} 个项目")
        
        if not headers:
            print("没有找到项目，无法测试删除功能")
            return
        
        # 2. 选择一个项目进行测试
        test_header = headers[0]
        print(f"\n选择测试项目: {test_header.hid} - {test_header.desc}")
        
        # 3. 查看该项目的REF和EO数量
        refs = ProjectRef.query.filter_by(header_id=test_header.id).all()
        print(f"该项目有 {len(refs)} 个REF")
        
        total_eos = 0
        for ref in refs:
            eos = ProjectEO.query.filter_by(ref_id=ref.id).all()
            total_eos += len(eos)
            print(f"  REF {ref.ref_number}: {len(eos)} 个EO")
        
        print(f"该项目总共有 {total_eos} 个EO")
        
        # 4. 询问是否继续删除
        response = input(f"\n是否要删除项目 {test_header.hid}？(y/N): ")
        if response.lower() != 'y':
            print("取消删除操作")
            return
        
        # 5. 执行删除操作
        try:
            # 删除所有相关的EO（通过REF关联）
            refs = ProjectRef.query.filter_by(header_id=test_header.id).all()
            for ref in refs:
                # 删除该REF下的所有EO
                eos = ProjectEO.query.filter_by(ref_id=ref.id).all()
                for eo in eos:
                    print(f"删除EO: {eo.eo_number}")
                    db.session.delete(eo)
                # 删除REF
                print(f"删除REF: {ref.ref_number}")
                db.session.delete(ref)
            
            # 删除项目主表
            print(f"删除Header: {test_header.hid}")
            db.session.delete(test_header)
            db.session.commit()
            
            print("✅ 项目删除成功！")
            
            # 6. 验证删除结果
            remaining_headers = ProjectHeader.query.all()
            print(f"删除后剩余项目数: {len(remaining_headers)}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 删除失败: {str(e)}")

if __name__ == "__main__":
    test_delete_header() 