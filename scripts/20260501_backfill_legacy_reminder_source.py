# -*- coding: utf-8 -*-
"""
回填旧式项目提醒 Todo 的 source_type / source_id
==========================================

背景：
旧版 reminder_utils.create_reminder_todo() 创建 Todo 时未设置
source_type / source_id，dedup 仅靠 title+description+category 全字段匹配，
description 略变就漏判 → 重复。

加固后版本（同一提交）改用：
  source_type='project_header_reminder'
  source_id=header.id
作为稳定 dedup 主键。

本脚本一次性回填历史 Todo 的这两个字段，让加固生效后能命中已有记录、
不会再次创建重复。

匹配逻辑：
  - category='项目提醒'
  - source_type IS NULL（仅处理尚未回填的）
  - title 形如 "项目提醒: {hid}"，从 title 解析 hid 反查 ProjectHeader
  - 找到唯一匹配的 header → 回填 source_type/source_id

前置条件：
  建议先跑 20260501_dedupe_project_reminder_todos.py --apply 清理重复记录，
  否则同一 header 会有多条 todo 试图共享同一 (source_type, source_id) 键。

运行方式:
    python scripts/20260501_backfill_legacy_reminder_source.py            # dry-run
    python scripts/20260501_backfill_legacy_reminder_source.py --apply    # 真正写入
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from App_new import create_app
from App_new.exts import db


TITLE_RE = re.compile(r'^项目提醒:\s*(\S+)$')
LEGACY_SOURCE_TYPE = 'project_header_reminder'


def main():
    apply_changes = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        from App_new.shared.models.Utilsmodels import Todo
        from App_new.business.projects.models.project import ProjectHeader

        todos = Todo.query.filter(
            Todo.category == '项目提醒',
            Todo.source_type.is_(None)
        ).all()
        print('=' * 100)
        print(f'扫描完毕：category="项目提醒" 且 source_type IS NULL 共 {len(todos)} 条')
        print('=' * 100)

        if not todos:
            print('没有需要回填的记录。')
            return

        # 解析 hid 并按 hid 反查 header
        hids_needed = set()
        title_hid_pairs = []
        unmatched_title = []
        for t in todos:
            m = TITLE_RE.match(t.title or '')
            if m:
                hid = m.group(1)
                title_hid_pairs.append((t, hid))
                hids_needed.add(hid)
            else:
                unmatched_title.append(t)

        # 一次查所有需要的 header
        headers = ProjectHeader.query.filter(ProjectHeader.hid.in_(hids_needed)).all()
        header_by_hid = {h.hid: h for h in headers}

        to_update = []  # (todo, header)
        no_header = []
        # 同一 header 下若仍有多条（说明清理脚本没跑或漏掉），逐组报告
        groups_by_hid = defaultdict(list)

        for todo, hid in title_hid_pairs:
            header = header_by_hid.get(hid)
            if not header:
                no_header.append((todo, hid))
                continue
            groups_by_hid[hid].append((todo, header))

        # 对于同一 hid 下多条记录，避免重复键冲突，只回填其中第一条，其余跳过并提示
        conflict_skipped = []
        for hid, items in groups_by_hid.items():
            if len(items) == 1:
                to_update.append(items[0])
            else:
                # 保留 due_date 最新的那条；其余跳过（建议先跑去重脚本）
                items_sorted = sorted(
                    items,
                    key=lambda x: (
                        0 if x[0].is_completed else 1,
                        -(x[0].due_date.timestamp() if x[0].due_date else 0),
                        -x[0].id
                    )
                )
                to_update.append(items_sorted[0])
                for skipped, _ in items_sorted[1:]:
                    conflict_skipped.append((skipped, hid))

        # 报告
        print(f'\n可回填 {len(to_update)} 条')
        for todo, header in to_update[:30]:
            print(f'  id={todo.id:>6}  hid={header.hid}  ->  source_type={LEGACY_SOURCE_TYPE}, source_id={header.id}')
        if len(to_update) > 30:
            print(f'  ...（其余 {len(to_update) - 30} 条略）')

        if unmatched_title:
            print(f'\n标题不匹配（无法解析 hid）{len(unmatched_title)} 条，跳过：')
            for t in unmatched_title[:10]:
                print(f'  id={t.id}  title={t.title!r}')
            if len(unmatched_title) > 10:
                print(f'  ...（其余 {len(unmatched_title) - 10} 条略）')

        if no_header:
            print(f'\n找不到对应的 ProjectHeader（hid 已被改/被删）{len(no_header)} 条，跳过：')
            for t, hid in no_header[:10]:
                print(f'  id={t.id}  hid={hid}')
            if len(no_header) > 10:
                print(f'  ...（其余 {len(no_header) - 10} 条略）')

        if conflict_skipped:
            print(f'\n同一 header 仍有多条 Todo（清理脚本未跑/未清干净）{len(conflict_skipped)} 条，本次跳过：')
            for t, hid in conflict_skipped[:10]:
                print(f'  id={t.id}  hid={hid}')
            print('  → 建议先跑 20260501_dedupe_project_reminder_todos.py --apply')

        if not apply_changes:
            print('\n[DRY-RUN] 仅预览，未修改数据库。加 --apply 执行回填。')
            return

        print('\n开始回填...')
        for todo, header in to_update:
            todo.source_type = LEGACY_SOURCE_TYPE
            todo.source_id = header.id
        db.session.commit()
        print(f'完成：已回填 {len(to_update)} 条 Todo。')


if __name__ == '__main__':
    main()
