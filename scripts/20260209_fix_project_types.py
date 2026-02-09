# -*- coding: utf-8 -*-
"""
修复项目类型数据不一致问题

数据库现状：
  id=1, code='airline', name='机票'      → 应改为 code='flight'
  id=9, code='miscellaneous', name='其他' → 应改为 code='other'
  id=10, code='Train', name='火车'        → 应改为 code='train'（小写）
  多条记录缺少 name_en

修复逻辑：
1. 修正 BusinessType 的 code 和 name_en 值
2. 重新计算所有项目的 type 字段

运行方式: python scripts/20260209_fix_project_types.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


# code 修正映射：旧code → (新code, name_en, product_code_prefix)
CODE_FIXES = {
    'airline': ('flight', 'Flight', 'FLT'),
    'miscellaneous': ('other', 'Other', 'OTH'),
    'Train': ('train', 'Train', 'TRN'),
    'coach': ('coach', 'Coach', 'COH'),
}

# 补全缺失的 name_en（针对 name_en 为 None 的记录）
NAME_EN_FIXES = {
    'flight': 'Flight',
    'other': 'Other',
    'train': 'Train',
    'coach': 'Coach',
}


def fix_project_types():
    app = create_app()

    with app.app_context():
        from App_new.shared.models.business_types import BusinessType
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.ref import ProjectRef

        print("=" * 60)
        print("修复项目类型数据")
        print("=" * 60)

        # ========== 第1步：显示当前 BusinessType 数据 ==========
        print("\n--- 第1步：当前 BusinessType 数据 ---")
        all_types = BusinessType.query.order_by(BusinessType.id).all()
        print(f"共有 {len(all_types)} 条记录:")
        for bt in all_types:
            ref_count = ProjectRef.query.filter_by(ref_type_id=bt.id).count()
            print(f"  id={bt.id}, code='{bt.code}', name='{bt.name}', name_en='{bt.name_en}', refs={ref_count}")

        # ========== 第2步：修正 BusinessType 的 code 和 name_en ==========
        print("\n--- 第2步：修正 BusinessType code 和 name_en ---")
        fixed_count = 0

        for bt in all_types:
            changed = False

            # 修正 code
            if bt.code in CODE_FIXES:
                new_code, new_name_en, new_prefix = CODE_FIXES[bt.code]
                old_code = bt.code
                bt.code = new_code
                bt.name_en = new_name_en
                if not bt.product_code_prefix:
                    bt.product_code_prefix = new_prefix
                print(f"  id={bt.id}: code '{old_code}' → '{new_code}', name_en → '{new_name_en}'")
                changed = True

            # 补全缺失的 name_en
            elif bt.name_en is None or bt.name_en == 'None':
                new_name_en = NAME_EN_FIXES.get(bt.code, bt.code.replace('_', ' ').title())
                bt.name_en = new_name_en
                print(f"  id={bt.id}: 补全 name_en → '{new_name_en}'")
                changed = True

            if changed:
                fixed_count += 1

        if fixed_count == 0:
            print("  所有记录已是正确状态")

        db.session.flush()

        # ========== 第3步：添加缺失的标准业务类型 ==========
        print("\n--- 第3步：检查缺失的标准业务类型 ---")
        existing_codes = {bt.code for bt in BusinessType.query.all()}
        missing_types = [
            {'code': 'transport', 'name': '交通', 'name_en': 'Transport', 'product_code_prefix': 'TRP', 'sort_order': 6},
            {'code': 'tour_package', 'name': '旅游套餐', 'name_en': 'Tour Package', 'product_code_prefix': 'PKG', 'sort_order': 16},
            {'code': 'rail_coach', 'name': '火车/大巴', 'name_en': 'Rail/Coach', 'product_code_prefix': 'TRN', 'sort_order': 12},
        ]

        for type_info in missing_types:
            if type_info['code'] not in existing_codes:
                new_type = BusinessType(**type_info, is_active=True)
                db.session.add(new_type)
                print(f"  新增: code='{type_info['code']}', name='{type_info['name']}'")
            else:
                print(f"  已存在: code='{type_info['code']}'")

        db.session.flush()

        # ========== 第4步：重新计算所有项目的 type ==========
        print("\n--- 第4步：重新计算项目 type ---")

        # 先显示修正后的 BusinessType 数据
        print("修正后的 BusinessType:")
        for bt in BusinessType.query.order_by(BusinessType.id).all():
            print(f"  id={bt.id}, code='{bt.code}', name='{bt.name}', name_en='{bt.name_en}'")

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

        print(f"\n共检查 {len(projects)} 个项目，更新了 {updated_count} 个项目的 type:")
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
