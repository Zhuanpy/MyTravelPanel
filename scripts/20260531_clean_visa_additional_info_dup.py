# -*- coding: utf-8 -*-
"""
清理签证文档"补充信息"中的重复数据。

处理两类历史重复：
  1) 字段内重复行：additional_info(旅行社补充信息) / applicant_additional_info(申请人补充信息)
     字段里出现重复的非空行 —— 去重(保留首次出现，保序，合并连续空行)。
  2) 重复记录：同 (visa_type_id, singapore_identity_id) 的多条 VisaDocuments —— 仅"报告"，
     不自动删除(可能含文档关联，需人工确认)。

运行方式:
  python scripts/20260531_clean_visa_additional_info_dup.py          # 仅报告，不改库
  python scripts/20260531_clean_visa_additional_info_dup.py --fix    # 执行字段内行去重
提示：若控制台报 UnicodeEncodeError，先执行 $env:PYTHONIOENCODING='utf-8'
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from sqlalchemy import func
from App_new import create_app
from App_new.exts import db

PLACEHOLDERS = {'', '待输入', 'None', 'none'}


def dedup_lines(text):
    """对多行文本按行去重：去掉重复的非空行，保留首次出现与顺序，连续空行合并为一个。"""
    if not text:
        return text, False
    out = []
    seen = set()
    for raw in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = raw.rstrip()
        key = line.strip()
        if key == '':
            if out and out[-1].strip() != '':
                out.append('')
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    # 去掉首尾空行
    while out and out[0].strip() == '':
        out.pop(0)
    while out and out[-1].strip() == '':
        out.pop()
    new_text = '\n'.join(out)
    return new_text, (new_text != (text or '').strip().replace('\r\n', '\n').replace('\r', '\n'))


app = create_app()

with app.app_context():
    from App_new.business.visa.models.Visamodels import VisaDocuments

    do_fix = '--fix' in sys.argv[1:]

    # ---- 1) 字段内重复行 ----
    rows = VisaDocuments.query.all()
    changed = 0
    print("=" * 70)
    print("字段内重复行检查")
    print("=" * 70)
    for r in rows:
        for field in ('additional_info', 'applicant_additional_info'):
            val = getattr(r, field) or ''
            if val.strip() in PLACEHOLDERS:
                continue
            new_val, did_change = dedup_lines(val)
            if did_change and new_val != val:
                orig_lines = len([x for x in val.replace('\r', '').split('\n') if x.strip()])
                new_lines = len([x for x in new_val.split('\n') if x.strip()])
                if orig_lines != new_lines:
                    print(f"  doc.id={r.id} vt={r.visa_type_id} ident={r.singapore_identity_id} {field}: 非空行 {orig_lines} -> {new_lines}")
                    if do_fix:
                        setattr(r, field, new_val)
                        changed += 1

    # ---- 2) 重复记录(仅报告) ----
    print("\n" + "=" * 70)
    print("重复记录组 (同 visa_type_id + singapore_identity_id，仅报告，不自动删除)")
    print("=" * 70)
    dup_groups = db.session.query(
        VisaDocuments.visa_type_id, VisaDocuments.singapore_identity_id, func.count(VisaDocuments.id)
    ).group_by(
        VisaDocuments.visa_type_id, VisaDocuments.singapore_identity_id
    ).having(func.count(VisaDocuments.id) > 1).all()
    for vt, ident, cnt in dup_groups:
        ids = [d.id for d in VisaDocuments.query.filter_by(visa_type_id=vt, singapore_identity_id=ident).all()]
        print(f"  visa_type_id={vt} identity_id={ident} count={cnt} ids={ids}")
    if not dup_groups:
        print("  无")

    if do_fix:
        db.session.commit()
        print(f"\n[已执行] 字段内行去重：修改 {changed} 个字段。重复记录未删除(见上方报告)。")
    else:
        print(f"\n[仅报告] 未修改任何数据。加 --fix 执行字段内行去重。")
