# -*- coding: utf-8 -*-
"""
清理项目资料清单中的重复记录（同一项目下同名 document_name 只保留最早一条）
运行方式: python scripts/cleanup_duplicate_doc_status.py [project_id]
不带参数则扫描所有项目，仅报告；带 project_id 则清理该项目。
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

app = create_app()

with app.app_context():
    from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
    from sqlalchemy import func

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    clean_all = (arg == '--all')
    target_pid = None if (arg is None or clean_all) else int(arg)
    do_delete = clean_all or (target_pid is not None)

    q = db.session.query(
        VisaProjectDocumentStatus.project_id,
        VisaProjectDocumentStatus.document_name,
        func.count(VisaProjectDocumentStatus.id)
    ).group_by(
        VisaProjectDocumentStatus.project_id,
        VisaProjectDocumentStatus.document_name
    ).having(func.count(VisaProjectDocumentStatus.id) > 1)

    if target_pid:
        q = q.filter(VisaProjectDocumentStatus.project_id == target_pid)

    dups = q.all()
    print("=" * 70)
    print("发现重复记录组数: {}".format(len(dups)))
    print("=" * 70)

    total_deleted = 0
    for pid, name, cnt in dups:
        rows = VisaProjectDocumentStatus.query.filter_by(
            project_id=pid, document_name=name
        ).order_by(VisaProjectDocumentStatus.id.asc()).all()
        keep = rows[0]
        remove = rows[1:]
        print("project_id={} | name={} | count={} -> keep id={}, remove {}".format(
            pid, name, cnt, keep.id, [r.id for r in remove]))
        if do_delete:
            for r in remove:
                db.session.delete(r)
                total_deleted += 1

    if do_delete:
        db.session.commit()
        scope = "project_id={}".format(target_pid) if target_pid else "ALL projects"
        print("\n已删除重复记录 {} 条 ({})".format(total_deleted, scope))
    else:
        print("\n[仅报告模式] 未删除任何记录。指定 project_id 或 --all 以执行清理。")
