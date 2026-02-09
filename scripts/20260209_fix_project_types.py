# -*- coding: utf-8 -*-
"""
修复项目类型数据不一致问题

问题：
1. 数据库中可能存在多条 name='机票' 的 BusinessType 记录，code 不同（如 'flight' 和 'airline'）
2. 部分 REF 引用了错误的 BusinessType，导致项目 type 被设置为 'airline' 或 'other'
3. Athina 导入映射 'Air' → 'air_ticket' 不存在，已修正为 'flight'

修复逻辑：
1. 检查并合并重复的 BusinessType 记录（保留 code='flight' 的标准记录）
2. 将引用旧记录的 REF 更新为引用正确的 BusinessType
3. 重新计算所有项目的 type 字段

运行方式: python scripts/20260209_fix_project_types.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def fix_project_types():
    app = create_app()

    with app.app_context():
        from sqlalchemy import text
        from App_new.shared.models.business_types import BusinessType
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.ref import ProjectRef

        print("=" * 60)
        print("修复项目类型数据")
        print("=" * 60)

        # ========== 第1步：检查 BusinessType 数据 ==========
        print("\n--- 第1步：检查 BusinessType 数据 ---")
        all_types = BusinessType.query.all()
        print(f"共有 {len(all_types)} 条 BusinessType 记录:")
        for bt in all_types:
            print(f"  id={bt.id}, code='{bt.code}', name='{bt.name}', name_en='{bt.name_en}'")

        # 查找所有 name='机票' 的记录
        flight_types = BusinessType.query.filter_by(name='机票').all()
        print(f"\nname='机票' 的记录数: {len(flight_types)}")
        for bt in flight_types:
            ref_count = ProjectRef.query.filter_by(ref_type_id=bt.id).count()
            print(f"  id={bt.id}, code='{bt.code}', name_en='{bt.name_en}' → 关联 {ref_count} 条 REF")

        # 确定标准的 flight BusinessType
        standard_flight = BusinessType.query.filter_by(code='flight').first()
        if not standard_flight:
            print("\n[警告] 未找到 code='flight' 的标准记录，需要先运行 init_default_types()")
            return

        print(f"\n标准机票类型: id={standard_flight.id}, code='{standard_flight.code}'")

        # ========== 第2步：合并重复的 BusinessType 记录 ==========
        print("\n--- 第2步：合并重复的 BusinessType 记录 ---")
        duplicate_flight_types = [bt for bt in flight_types if bt.id != standard_flight.id]

        if not duplicate_flight_types:
            print("未发现重复的机票类型记录")
        else:
            for dup in duplicate_flight_types:
                # 将引用旧记录的 REF 更新为引用标准记录
                affected_refs = ProjectRef.query.filter_by(ref_type_id=dup.id).count()
                print(f"  将 {affected_refs} 条 REF 从 BusinessType id={dup.id}(code='{dup.code}') 迁移到 id={standard_flight.id}(code='flight')")

                ProjectRef.query.filter_by(ref_type_id=dup.id).update(
                    {'ref_type_id': standard_flight.id},
                    synchronize_session=False
                )

                # 删除重复记录
                db.session.delete(dup)
                print(f"  已删除重复记录 id={dup.id}")

        # 同样检查其他可能的重复类型（如 name='其他' 但 code 不是 'other'）
        other_standard = BusinessType.query.filter_by(code='other').first()
        if other_standard:
            other_duplicates = BusinessType.query.filter(
                BusinessType.name == '其他',
                BusinessType.id != other_standard.id
            ).all()
            for dup in other_duplicates:
                affected_refs = ProjectRef.query.filter_by(ref_type_id=dup.id).count()
                if affected_refs > 0:
                    print(f"  将 {affected_refs} 条 REF 从 '其他' BusinessType id={dup.id}(code='{dup.code}') 迁移到 id={other_standard.id}(code='other')")
                    ProjectRef.query.filter_by(ref_type_id=dup.id).update(
                        {'ref_type_id': other_standard.id},
                        synchronize_session=False
                    )
                db.session.delete(dup)
                print(f"  已删除重复记录 id={dup.id}")

        db.session.flush()

        # ========== 第2.5步：修复有机票数据但 ref_type_id 指向错误类型的 REF ==========
        print("\n--- 第2.5步：修复机票REF的类型指向 ---")
        from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger

        # 找到所有有航段数据的 REF ID
        refs_with_segments = db.session.query(ProjectFlightSegment.ref_id).distinct().all()
        refs_with_passengers = db.session.query(ProjectFlightPassenger.ref_id).distinct().all()
        flight_ref_ids = set(r[0] for r in refs_with_segments) | set(r[0] for r in refs_with_passengers)
        print(f"共发现 {len(flight_ref_ids)} 条有机票数据（航段/乘客）的 REF")

        # 检查这些 REF 中 ref_type_id 不是 flight 的
        wrong_type_refs = ProjectRef.query.filter(
            ProjectRef.id.in_(flight_ref_ids),
            ProjectRef.ref_type_id != standard_flight.id
        ).all()

        if wrong_type_refs:
            print(f"其中 {len(wrong_type_refs)} 条 REF 的类型指向不正确，修复中:")
            for ref in wrong_type_refs:
                wrong_bt = BusinessType.query.get(ref.ref_type_id)
                wrong_code = wrong_bt.code if wrong_bt else 'NULL'
                print(f"  REF id={ref.id} ref_number='{ref.ref_number}': ref_type '{wrong_code}' → 'flight'")
                ref.ref_type_id = standard_flight.id
        else:
            print("所有有机票数据的 REF 类型指向正确")

        # 同时检查 extra_info 中 book_type 为 Air/Airline 的 REF
        import json
        air_type_refs = ProjectRef.query.filter(
            ProjectRef.extra_info.ilike('%"book_type": "Air%'),
            ProjectRef.ref_type_id != standard_flight.id
        ).all()

        if air_type_refs:
            print(f"发现 {len(air_type_refs)} 条 extra_info 标记为 Air/Airline 但类型不正确的 REF:")
            for ref in air_type_refs:
                wrong_bt = BusinessType.query.get(ref.ref_type_id)
                wrong_code = wrong_bt.code if wrong_bt else 'NULL'
                print(f"  REF id={ref.id} ref_number='{ref.ref_number}': ref_type '{wrong_code}' → 'flight'")
                ref.ref_type_id = standard_flight.id

        db.session.flush()

        # ========== 第3步：重新计算所有项目的 type ==========
        print("\n--- 第3步：重新计算项目 type ---")
        projects = ProjectHeader.query.all()
        updated_count = 0
        type_changes = {}

        for project in projects:
            old_type = project.type
            project.update_type_from_refs()
            new_type = project.type

            if old_type != new_type:
                updated_count += 1
                change_key = f"'{old_type}' → '{new_type}'"
                type_changes[change_key] = type_changes.get(change_key, 0) + 1

        print(f"共检查 {len(projects)} 个项目，更新了 {updated_count} 个项目的 type:")
        for change, count in sorted(type_changes.items(), key=lambda x: -x[1]):
            print(f"  {change}: {count} 个")

        # ========== 提交 ==========
        try:
            db.session.commit()
            print("\n✓ 所有修复已提交")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ 提交失败: {e}")
            raise


if __name__ == '__main__':
    fix_project_types()
