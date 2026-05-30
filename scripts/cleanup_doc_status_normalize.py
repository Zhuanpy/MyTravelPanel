# -*- coding: utf-8 -*-
"""
清理资料清单的"项目符号前缀"历史重复数据。

背景：旧版本同步把资料名存成带 "• " 前缀（如 "• 护照首页"），新版本存成干净名
（如 "护照首页"）。两者被当成不同记录，造成同一资料重复加载。

本脚本按"去前缀后的名称"归并：
  - 同名(归一化后)只保留一条，统一用干净名（去掉 "• " 前缀）
  - 合并已准备状态：任意一条为已准备，则保留的记录为已准备（不丢进度）
  - 合并备注：保留第一条非空备注
  - 单条记录但带前缀的，也会重命名为干净名

运行方式:
  python scripts/cleanup_doc_status_normalize.py            # 仅报告(全部项目，不修改)
  python scripts/cleanup_doc_status_normalize.py 483        # 清理指定项目
  python scripts/cleanup_doc_status_normalize.py --all      # 清理全部项目
提示：若控制台报 UnicodeEncodeError，先执行 $env:PYTHONIOENCODING='utf-8'
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保标准输出为 UTF-8，避免打印 • 等字符时在某些控制台编码下报错
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from App_new import create_app
from App_new.exts import db

# 需要从名称开头剥离的项目符号字符
BULLET_CHARS = '•·‣◦∙●○*'


def normalize(name):
    """去掉名称开头的项目符号和空白，返回干净名称。"""
    s = (name or '').strip()
    while s and s[0] in BULLET_CHARS:
        s = s[1:].strip()
    return s


app = create_app()

with app.app_context():
    from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    clean_all = (arg == '--all')
    target_pid = None if (arg is None or clean_all) else int(arg)
    do_delete = clean_all or (target_pid is not None)

    q = VisaProjectDocumentStatus.query
    if target_pid:
        q = q.filter_by(project_id=target_pid)
    rows = q.order_by(VisaProjectDocumentStatus.id.asc()).all()

    # 按 (project_id, 归一化名称) 分组
    groups = {}
    for r in rows:
        key = (r.project_id, normalize(r.document_name))
        groups.setdefault(key, []).append(r)

    deleted = 0
    renamed = 0
    merged_groups = 0

    print("=" * 70)
    for (pid, norm), grp in sorted(groups.items()):
        names = [g.document_name for g in grp]
        needs_merge = len(grp) > 1
        needs_rename = any(g.document_name != norm for g in grp)
        if not needs_merge and not needs_rename:
            continue

        # 合并状态与备注
        merged_ready = any(bool(g.is_ready) for g in grp)
        merged_notes = ''
        for g in grp:
            if g.notes and g.notes.strip():
                merged_notes = g.notes
                break

        # 选存活记录：优先已是干净名的，否则取最早一条
        survivor = next((g for g in grp if g.document_name == norm), grp[0])
        remove = [g for g in grp if g.id != survivor.id]

        print("project_id={} | 归一名='{}' | 原始={} | 保留 id={}(ready={}) | 删除 {}".format(
            pid, norm, names, survivor.id, merged_ready, [g.id for g in remove]))

        if do_delete:
            survivor.document_name = norm
            survivor.is_ready = merged_ready
            if (not survivor.notes or not survivor.notes.strip()) and merged_notes:
                survivor.notes = merged_notes
            if survivor.document_name != norm:
                renamed += 1
            for g in remove:
                db.session.delete(g)
                deleted += 1
            merged_groups += 1

    if do_delete:
        db.session.commit()
        scope = "project_id={}".format(target_pid) if target_pid else "ALL projects"
        print("\n完成 ({}): 归并 {} 组, 删除重复 {} 条".format(scope, merged_groups, deleted))
    else:
        print("\n[仅报告模式] 未修改任何数据。指定 project_id 或 --all 执行清理。")
