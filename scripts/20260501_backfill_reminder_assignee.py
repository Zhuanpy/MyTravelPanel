# -*- coding: utf-8 -*-
"""
回填项目提醒 Todo 的负责人（assigned_to）
==================================

背景：
旧逻辑创建项目提醒 todo 时未设置 assigned_to / assigned_by，
导致团队任务列表显示"未分配"。
本次代码加固后新建提醒会自动把当前用户设为负责人，
本脚本一次性回填历史记录。

匹配优先级（找到非空就用）：
1. todo.user_id（创建者）
2. 关联 ProjectHeader 的 staff_id（项目责任人）
   - source_type='project_reminder' / 'project_header_reminder' 时直接拿 source_id 当 header_id
   - 否则按标题反查：[Hxxx] ... 或 项目提醒: Hxxx

不会覆盖已有 assigned_to。

运行方式:
    python scripts/20260501_backfill_reminder_assignee.py            # dry-run
    python scripts/20260501_backfill_reminder_assignee.py --apply
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from App_new import create_app
from App_new.exts import db


HID_TITLE_PATTERNS = [
    re.compile(r'^\[(\S+)\]'),       # [H1030] xxx
    re.compile(r'^项目提醒:\s*(\S+)$'),  # 项目提醒: H1030
]


def parse_hid(title):
    if not title:
        return None
    for p in HID_TITLE_PATTERNS:
        m = p.match(title)
        if m:
            return m.group(1)
    return None


def main():
    apply_changes = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        from App_new.shared.models.Utilsmodels import Todo
        from App_new.business.projects.models.project import ProjectHeader

        todos = Todo.query.filter(
            Todo.category == '项目提醒',
            Todo.assigned_to.is_(None)
        ).all()
        print('=' * 100)
        print(f'扫描完毕：category="项目提醒" 且 assigned_to IS NULL 共 {len(todos)} 条')
        print('=' * 100)

        if not todos:
            print('没有需要回填的记录。')
            return

        # 预查 ProjectHeader：先收集所有需要的 header_id 和 hid
        header_ids_needed = set()
        hids_needed = set()
        for t in todos:
            if t.source_type in ('project_reminder', 'project_header_reminder') and t.source_id:
                header_ids_needed.add(t.source_id)
            else:
                hid = parse_hid(t.title)
                if hid:
                    hids_needed.add(hid)

        headers_by_id = {}
        if header_ids_needed:
            for h in ProjectHeader.query.filter(ProjectHeader.id.in_(header_ids_needed)).all():
                headers_by_id[h.id] = h
        headers_by_hid = {}
        if hids_needed:
            for h in ProjectHeader.query.filter(ProjectHeader.hid.in_(hids_needed)).all():
                headers_by_hid[h.hid] = h

        to_update = []  # (todo, assignee_id, source_label)
        no_assignee = []

        for t in todos:
            assignee_id = None
            source_label = ''

            # 1. 最优先：todo.user_id（创建者）
            if t.user_id:
                assignee_id = t.user_id
                source_label = f'user_id={t.user_id} (创建者)'
            else:
                # 2. fallback：关联 header 的 staff_id
                header = None
                if t.source_type in ('project_reminder', 'project_header_reminder') and t.source_id:
                    header = headers_by_id.get(t.source_id)
                if not header:
                    hid = parse_hid(t.title)
                    if hid:
                        header = headers_by_hid.get(hid)
                if header and getattr(header, 'staff_id', None):
                    assignee_id = header.staff_id
                    source_label = f'header.staff_id={header.staff_id} (hid={header.hid})'

            if assignee_id:
                to_update.append((t, assignee_id, source_label))
            else:
                no_assignee.append(t)

        # 报告
        print(f'\n可回填 {len(to_update)} 条')
        for t, assignee_id, label in to_update[:30]:
            print(f'  id={t.id:>6}  title={t.title[:40]:<40}  ->  assigned_to={assignee_id}  ({label})')
        if len(to_update) > 30:
            print(f'  ...（其余 {len(to_update) - 30} 条略）')

        if no_assignee:
            print(f'\n无法确定负责人（user_id / header.staff_id 都没值）{len(no_assignee)} 条，跳过：')
            for t in no_assignee[:10]:
                print(f'  id={t.id}  title={t.title!r}  source={t.source_type}/{t.source_id}')
            if len(no_assignee) > 10:
                print(f'  ...（其余 {len(no_assignee) - 10} 条略）')

        if not apply_changes:
            print('\n[DRY-RUN] 仅预览，未修改数据库。加 --apply 执行回填。')
            return

        print('\n开始回填...')
        now = datetime.utcnow()
        for t, assignee_id, _ in to_update:
            t.assigned_to = assignee_id
            t.assigned_by = assignee_id
            t.assigned_at = now
        db.session.commit()
        print(f'完成：已回填 {len(to_update)} 条 Todo。')


if __name__ == '__main__':
    main()
