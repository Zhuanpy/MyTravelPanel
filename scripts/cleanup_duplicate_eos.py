#!/usr/bin/env python3
"""
清理重复的EO数据脚本
确保每个REF只有一个EO，删除多余的EO记录
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectRef, ProjectEO
from sqlalchemy import text

def cleanup_duplicate_eos():
    """清理重复的EO数据"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始清理重复的EO数据...")
            
            # 查找有多个EO的REF
            duplicate_refs = db.session.execute(text("""
                SELECT ref_id, COUNT(*) as eo_count
                FROM project_eos
                GROUP BY ref_id
                HAVING COUNT(*) > 1
                ORDER BY eo_count DESC
            """)).fetchall()
            
            if not duplicate_refs:
                print("没有发现重复的EO数据")
                return
            
            print(f"发现 {len(duplicate_refs)} 个REF有多个EO:")
            
            total_deleted = 0
            
            for ref_record in duplicate_refs:
                ref_id = ref_record.ref_id
                eo_count = ref_record.eo_count
                
                # 获取REF信息
                ref = ProjectRef.query.get(ref_id)
                if not ref:
                    print(f"  REF ID {ref_id} 不存在，跳过")
                    continue
                
                print(f"  REF {ref.ref_number} (ID: {ref_id}) 有 {eo_count} 个EO")
                
                # 获取该REF的所有EO，按创建时间排序
                eos = ProjectEO.query.filter_by(ref_id=ref_id).order_by(ProjectEO.created_at).all()
                
                # 保留第一个EO，删除其余的
                keep_eo = eos[0]
                delete_eos = eos[1:]
                
                print(f"    保留: {keep_eo.eo_number} (创建时间: {keep_eo.created_at})")
                
                for delete_eo in delete_eos:
                    print(f"    删除: {delete_eo.eo_number} (创建时间: {delete_eo.created_at})")
                    db.session.delete(delete_eo)
                    total_deleted += 1
            
            # 提交删除操作
            db.session.commit()
            print(f"\n清理完成！总共删除了 {total_deleted} 个重复的EO记录")
            
            # 验证清理结果
            remaining_duplicates = db.session.execute(text("""
                SELECT ref_id, COUNT(*) as eo_count
                FROM project_eos
                GROUP BY ref_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if remaining_duplicates:
                print(f"警告：仍有 {len(remaining_duplicates)} 个REF有多个EO")
                for ref_record in remaining_duplicates:
                    ref = ProjectRef.query.get(ref_record.ref_id)
                    print(f"  REF {ref.ref_number if ref else 'Unknown'} (ID: {ref_record.ref_id})")
            else:
                print("验证通过：所有REF现在都只有一个EO")
                
        except Exception as e:
            db.session.rollback()
            print(f"清理过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    cleanup_duplicate_eos() 