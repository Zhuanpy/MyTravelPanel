# -*- coding: utf-8 -*-
"""
迁移旧版项目提醒到新系统
======================

背景：
旧版项目提醒由 ProjectHeader.reminder_event/reminder_date 单字段驱动，
通过 reminder_utils.create_reminder_todo 同步成 Todo
(source_type='project_header_reminder')。

新版系统是 ProjectReminder 表 + Todo (source_type='project_reminder')，
支持每个项目多条提醒。项目详情页只读新系统。

双系统并存导致：
- 同一项目可能同时有旧式和新式 Todo
- 用户在项目详情页完成新式 Todo 后，旧式 Todo 仍未完成 → 团队任务列表"已逾期"
- 数据不同步

本次彻底退役旧系统。脚本逻辑：

  对每条 source_type='project_header_reminder' 的旧式 Todo（设此 Todo 关联的
  header_id = source_id），按 header 分组：

  1. 该 header 已存在任意 source_type='project_reminder' 新式 Todo
     → 旧式是冗余 → 直接删除旧式
  2. 该 header 没有新式 Todo
     → 把旧式 Todo 转成新式：source_type='project_reminder'，title 改为
       "[hid] {reminder_event}"，description 同步成新格式；同时在
       ProjectReminder 表插一条对应记录
     → 然后删除转换前的旧式记录（实际是 update + 同步插 ProjectReminder）

简单起见，本脚本采用做法 1.5：
  - 有新式 → 删除旧式
  - 没有新式 → 把旧式 Todo 直接 in-place 改造成新式（修改 source_type / title /
    description；同时插 ProjectReminder 记录用于双向引用）

运行方式:
    python scripts/20260501_migrate_legacy_reminder_to_new_system.py            # dry-run
    python scripts/20260501_migrate_legacy_reminder_to_new_system.py --apply
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from datetime import datetime
from App_new import create_app
from App_new.exts import db


def main():
    apply_changes = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        from App_new.shared.models.Utilsmodels import Todo
        from App_new.business.projects.models.project import ProjectHeader, ProjectReminder

        legacy_todos = Todo.query.filter(
            Todo.category == '项目提醒',
            Todo.source_type == 'project_header_reminder'
        ).all()
        print('=' * 100)
        print(f'扫描完毕：legacy todos (source_type=project_header_reminder) 共 {len(legacy_todos)} 条')
        print('=' * 100)

        if not legacy_todos:
            print('没有需要迁移的旧式记录。')
            return

        # 预查每个 header 的新式 Todo 数量
        header_ids = {t.source_id for t in legacy_todos if t.source_id}
        new_style_counts = dict(
            db.session.query(Todo.source_id, db.func.count(Todo.id))
            .filter(
                Todo.source_type == 'project_reminder',
                Todo.source_id.in_(header_ids)
            )
            .group_by(Todo.source_id)
            .all()
        )
        # 预查 header 数据
        headers_by_id = {
            h.id: h for h in ProjectHeader.query.filter(ProjectHeader.id.in_(header_ids)).all()
        }

        to_delete = []  # 已有新式 → 删旧式
        to_convert = []  # 没新式 → 改造成新式
        no_header = []  # 找不到 header 的孤儿

        for t in legacy_todos:
            header = headers_by_id.get(t.source_id)
            if not header:
                no_header.append(t)
                continue
            if new_style_counts.get(t.source_id, 0) > 0:
                to_delete.append((t, header))
            else:
                to_convert.append((t, header))

        # 报告
        print(f'\n[删除] 已有新式 Todo，旧式冗余 {len(to_delete)} 条')
        for t, h in to_delete[:30]:
            comp = '已完成' if t.is_completed else '未完成'
            print(f'  id={t.id:>6}  hid={h.hid}  due={t.due_date}  {comp}')
        if len(to_delete) > 30:
            print(f'  ...（其余 {len(to_delete) - 30} 条略）')

        print(f'\n[转换] 没有新式 Todo，原地改造成新式 {len(to_convert)} 条')
        for t, h in to_convert[:30]:
            event = h.reminder_event or '(空)'
            print(f'  id={t.id:>6}  hid={h.hid}  reminder_event="{event[:40]}"  due={t.due_date}')
        if len(to_convert) > 30:
            print(f'  ...（其余 {len(to_convert) - 30} 条略）')

        if no_header:
            print(f'\n[孤儿] 找不到对应 header（已被删除？）{len(no_header)} 条，将一并删除')
            for t in no_header[:10]:
                print(f'  id={t.id}  source_id={t.source_id}  title={t.title!r}')

        if not apply_changes:
            print('\n[DRY-RUN] 仅预览，未修改数据库。加 --apply 执行迁移。')
            return

        print('\n开始迁移...')

        # 1) 删除冗余旧式
        for t, _ in to_delete:
            db.session.delete(t)

        # 2) 删除孤儿
        for t in no_header:
            db.session.delete(t)

        # 3) 转换为新式
        for t, h in to_convert:
            event = h.reminder_event or (t.title or '').replace(f'项目提醒: {h.hid}', '').strip() or '提醒'
            new_title = f'[{h.hid}] {event}'
            new_desc = f'项目: {h.hid}\n描述: {h.desc or ""}\n提醒事件: {event}'
            # 修改 Todo 自身：source_type / title / description
            t.source_type = 'project_reminder'
            t.title = new_title
            t.description = new_desc
            t.updated_at = datetime.utcnow()
            # 在 ProjectReminder 表插入一条对应记录（如果尚未有同 header_id + 同 event 的）
            existing_pr = ProjectReminder.query.filter_by(
                header_id=h.id,
                reminder_event=event
            ).first()
            if not existing_pr and h.reminder_date:
                pr = ProjectReminder(
                    header_id=h.id,
                    reminder_event=event,
                    reminder_date=h.reminder_date if hasattr(h.reminder_date, 'year') and not isinstance(h.reminder_date, datetime) else h.reminder_date.date() if isinstance(h.reminder_date, datetime) else None,
                    is_completed=t.is_completed
                )
                db.session.add(pr)

        db.session.commit()
        print(f'完成：删除 {len(to_delete) + len(no_header)} 条 + 转换 {len(to_convert)} 条')


if __name__ == '__main__':
    main()
