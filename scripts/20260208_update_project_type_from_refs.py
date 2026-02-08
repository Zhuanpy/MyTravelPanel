# -*- coding: utf-8 -*-
"""
批量更新所有项目的type字段（根据REF业务类型自动推断）

规则：
- 所有REF类型相同 → 使用该类型的code
- 任何REF包含tour类型 → 使用 'tour'
- 其它混合类型 → 使用 'package'
- 没有REF的项目 → 跳过不更新

运行方式: python scripts/20260208_update_project_type_from_refs.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()


def update_all_project_types():
    """批量更新所有项目的type字段"""
    from App_new.business.projects.models.project import ProjectHeader

    with app.app_context():
        headers = ProjectHeader.query.all()
        total = len(headers)
        updated = 0
        skipped = 0

        print(f"共 {total} 个项目，开始更新...")

        for header in headers:
            old_type = header.type
            header.update_type_from_refs()
            new_type = header.type

            if old_type != new_type:
                updated += 1
                print(f"  {header.hid}: {old_type or '(空)'} -> {new_type}")
            else:
                skipped += 1

        db.session.commit()
        print(f"\n完成！更新 {updated} 个项目，跳过 {skipped} 个（类型未变或无REF）")


if __name__ == '__main__':
    update_all_project_types()
