#!/usr/bin/env python3
"""
测试REF和EO的一对一关系脚本
验证修复是否成功
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectRef, ProjectEO
from sqlalchemy import text

def test_ref_eo_relationship():
    """测试REF和EO的一对一关系"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始测试REF和EO的一对一关系...")
            
            # 检查是否还有重复的EO
            duplicate_refs = db.session.execute(text("""
                SELECT ref_id, COUNT(*) as eo_count
                FROM project_eos
                GROUP BY ref_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicate_refs:
                print(f"❌ 发现 {len(duplicate_refs)} 个REF仍有多个EO:")
                for ref_record in duplicate_refs:
                    ref = ProjectRef.query.get(ref_record.ref_id)
                    print(f"  REF {ref.ref_number if ref else 'Unknown'} (ID: {ref_record.ref_id}) 有 {ref_record.eo_count} 个EO")
            else:
                print("✅ 所有REF都只有一个EO")
            
            # 检查约束是否存在
            constraints = db.session.execute(text("""
                SELECT CONSTRAINT_NAME 
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_NAME = 'project_eos' 
                AND CONSTRAINT_TYPE = 'UNIQUE'
                AND CONSTRAINT_NAME LIKE '%ref_id%'
            """)).fetchall()
            
            if constraints:
                print("✅ 数据库约束已添加")
                for constraint in constraints:
                    print(f"  约束名称: {constraint[0]}")
            else:
                print("❌ 数据库约束未找到")
            
            # 测试模型关系
            refs_with_eos = ProjectRef.query.filter(ProjectRef.eos.isnot(None)).limit(5).all()
            print(f"\n测试模型关系 - 前5个有EO的REF:")
            for ref in refs_with_eos:
                if ref.eos:
                    print(f"  REF {ref.ref_number} -> EO {ref.eos.eo_number}")
                else:
                    print(f"  REF {ref.ref_number} -> 无EO")
            
            # 测试快速创建EO功能
            refs_without_eos = ProjectRef.query.filter(ProjectRef.eos.is_(None)).limit(3).all()
            if refs_without_eos:
                print(f"\n发现 {len(refs_without_eos)} 个REF没有EO:")
                for ref in refs_without_eos:
                    print(f"  REF {ref.ref_number} (ID: {ref.id})")
            else:
                print("\n所有REF都有EO")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_ref_eo_relationship() 