# -*- coding: utf-8 -*-
"""修正 business_types 表中"其他"类型的 code 字段

问题：已有 name='其他' 的记录但 code 不是 'other'，
导致创建 other 类型 REF 时因 name 唯一约束冲突而失败。

运行方式: python scripts/20260212_fix_business_type_other.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def fix_business_type_other():
    app = create_app()

    with app.app_context():
        from App_new.shared.models.business_types import BusinessType

        # 查看当前状态
        print("=== 修正前 ===")
        records = BusinessType.query.filter(
            db.or_(BusinessType.name == '其他', BusinessType.code == 'other')
        ).all()

        if not records:
            print("未找到 name='其他' 或 code='other' 的记录，无需修正")
            return

        for r in records:
            print(f"  ID={r.id}, code='{r.code}', name='{r.name}', name_en='{r.name_en}'")

        # 检查是否已经正确
        correct = BusinessType.query.filter_by(code='other', name='其他').first()
        if correct:
            print(f"\n记录已正确 (ID={correct.id})，无需修正")
            return

        # 查找 name='其他' 但 code 不是 'other' 的记录
        wrong = BusinessType.query.filter(
            BusinessType.name == '其他',
            BusinessType.code != 'other'
        ).first()

        if wrong:
            old_code = wrong.code
            wrong.code = 'other'
            if not wrong.name_en:
                wrong.name_en = 'Other'
            db.session.commit()
            print(f"\n已修正: ID={wrong.id}, code '{old_code}' → 'other'")
        else:
            # 可能存在 code='other' 但 name 不同的情况
            other_code = BusinessType.query.filter_by(code='other').first()
            if other_code:
                print(f"\n已存在 code='other' 的记录 (ID={other_code.id}, name='{other_code.name}')，请手动检查")
            else:
                print("\n未找到需要修正的记录")

        # 验证结果
        print("\n=== 修正后 ===")
        records = BusinessType.query.filter(
            db.or_(BusinessType.name == '其他', BusinessType.code == 'other')
        ).all()
        for r in records:
            print(f"  ID={r.id}, code='{r.code}', name='{r.name}', name_en='{r.name_en}'")


if __name__ == '__main__':
    fix_business_type_other()
