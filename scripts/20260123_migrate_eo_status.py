"""
EO状态迁移脚本
将draft状态改为confirmed，将cancelled状态改为void

运行方式: python scripts/20260123_migrate_eo_status.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()


def migrate_eo_status():
    """迁移EO状态：draft→confirmed, cancelled→void"""
    from App_new.business.projects.models.eo import ProjectEO

    with app.app_context():
        # 统计当前状态分布
        all_eos = ProjectEO.query.all()
        status_counts = {}
        for eo in all_eos:
            status_counts[eo.status] = status_counts.get(eo.status, 0) + 1

        print("当前EO状态分布:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        print(f"  总计: {len(all_eos)}")
        print()

        # 迁移 draft → confirmed
        draft_eos = ProjectEO.query.filter_by(status='draft').all()
        print(f"需要迁移 draft → confirmed: {len(draft_eos)} 条")
        for eo in draft_eos:
            eo.status = 'confirmed'

        # 迁移 cancelled → void
        cancelled_eos = ProjectEO.query.filter_by(status='cancelled').all()
        print(f"需要迁移 cancelled → void: {len(cancelled_eos)} 条")
        for eo in cancelled_eos:
            eo.status = 'void'

        if len(draft_eos) == 0 and len(cancelled_eos) == 0:
            print("\n无需迁移，所有EO状态已经是最新的。")
            return

        # 确认执行
        confirm = input(f"\n确认执行迁移？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消迁移。")
            return

        db.session.commit()
        print(f"\n迁移完成！")
        print(f"  draft → confirmed: {len(draft_eos)} 条")
        print(f"  cancelled → void: {len(cancelled_eos)} 条")

        # 验证迁移结果
        remaining_draft = ProjectEO.query.filter_by(status='draft').count()
        remaining_cancelled = ProjectEO.query.filter_by(status='cancelled').count()
        if remaining_draft == 0 and remaining_cancelled == 0:
            print("\n验证通过：已无draft和cancelled状态的EO记录。")
        else:
            print(f"\n警告：仍有 draft={remaining_draft}, cancelled={remaining_cancelled} 条记录！")


if __name__ == '__main__':
    migrate_eo_status()
