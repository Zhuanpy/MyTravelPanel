# -*- coding: utf-8 -*-
"""
清理 Todo 表中"项目提醒"类的重复记录
================================

背景：
APScheduler 多 worker 并发 bug（已在 commit 791756b 修复）期间，
定时同步 sync_project_reminders 在多个 worker 同时跑过，
reminder_utils.create_reminder_todo 的 dedup（先 SELECT 后 INSERT，
无唯一约束/无锁）出现竞态，导致同一项目同一事件被插入了多份。

清理逻辑：
1. 只针对 category='项目提醒' 类型（这是发生重复的旧式 Todo）
2. 按 (title, description, category) 分组
3. 每组若只有 1 条，跳过；若有多条，保留 1 条，其余删除
4. 保留优先级（哪条留下来）：
   - 已完成 (is_completed=True) 优先（避免丢失完成记录）
   - 然后按 due_date 倒序（与 dedup 更新逻辑一致：每次同步会把 due_date
     更新为项目的最新 reminder_date）
   - 然后按 id 倒序（最新创建的优先）

运行方式:
    python scripts/20260501_dedupe_project_reminder_todos.py            # dry-run 预览
    python scripts/20260501_dedupe_project_reminder_todos.py --apply    # 真正删除
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from App_new import create_app
from App_new.exts import db


def pick_keeper(todos):
    """从一组重复 todo 中选出要保留的那条。

    排序键（升序排，取第 0 个）：
      (是否未完成 0/1, -due_date_unix, -id)
    -> 已完成 < 未完成；同完成度下，due_date 越大越靠前；同 due_date 时 id 越大越靠前。
    """
    def key(t):
        completed_rank = 0 if t.is_completed else 1
        # 用负数实现倒序；None 当作很小
        due_ts = t.due_date.timestamp() if t.due_date else 0
        return (completed_rank, -due_ts, -t.id)

    return sorted(todos, key=key)[0]


def main():
    apply_changes = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        from App_new.shared.models.Utilsmodels import Todo

        todos = Todo.query.filter(Todo.category == '项目提醒').all()
        print('=' * 100)
        print(f'扫描完毕：category="项目提醒" 共 {len(todos)} 条')
        print('=' * 100)

        groups = defaultdict(list)
        for t in todos:
            key = (t.title or '', t.description or '', t.category or '')
            groups[key].append(t)

        dup_groups = [(k, v) for k, v in groups.items() if len(v) > 1]
        print(f'发现 {len(dup_groups)} 组重复（每组 >= 2 条）')

        if not dup_groups:
            print('没有需要清理的重复记录。')
            return

        total_to_delete = 0
        delete_ids = []
        for (title, _desc, _cat), records in dup_groups:
            keeper = pick_keeper(records)
            losers = [r for r in records if r.id != keeper.id]
            total_to_delete += len(losers)

            print(f'\n[{title}]  共 {len(records)} 条')
            for r in records:
                marker = ' <- 保留' if r.id == keeper.id else '   删除'
                due = r.due_date.strftime('%Y-%m-%d %H:%M') if r.due_date else '-'
                completed = '已完成' if r.is_completed else '未完成'
                print(f'   {marker}  id={r.id:>6}  due={due}  {completed}  created={r.created_at}')

            delete_ids.extend(r.id for r in losers)

        print('\n' + '=' * 100)
        print(f'合计待删除：{total_to_delete} 条（保留 {len(dup_groups)} 条）')
        print('=' * 100)

        if not apply_changes:
            print('\n[DRY-RUN] 仅预览，未修改数据库。加 --apply 执行删除。')
            return

        print('\n开始删除...')
        deleted = Todo.query.filter(Todo.id.in_(delete_ids)).delete(synchronize_session=False)
        db.session.commit()
        print(f'完成：已删除 {deleted} 条重复 Todo。')


if __name__ == '__main__':
    main()
