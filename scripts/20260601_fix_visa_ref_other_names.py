# -*- coding: utf-8 -*-
"""
数据脚本：修正自动创建的签证 REF 名称（描述）—— 把 "OTHER ... VISA" 这类
因旧映射表缺失而生成的错误名称，按关联的签证项目/签证类型重新生成为
"{国家英文名} {签证类型}"。

运行方式:
  python scripts/20260601_fix_visa_ref_other_names.py          # 仅报告
  python scripts/20260601_fix_visa_ref_other_names.py --fix    # 执行修正
提示：若控制台报 UnicodeEncodeError，先执行 $env:PYTHONIOENCODING='utf-8'
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.visa.models.Visamodels import VisaProject, VisaTypes
    from App_new.shared.models.business_types import BusinessType

    do_fix = '--fix' in sys.argv[1:]

    visa_bt = BusinessType.query.filter_by(code='visa').first()
    if not visa_bt:
        print('未找到签证业务类型, 退出')
        sys.exit(0)

    # 找出名称以 OTHER 开头的签证 REF（旧映射表生成的错误名称）
    refs = ProjectRef.query.filter(
        ProjectRef.ref_type_id == visa_bt.id,
        ProjectRef.description.like('OTHER %')
    ).all()

    print(f"待检查的签证REF(名称以 OTHER 开头): {len(refs)}")
    fixed = 0
    for ref in refs:
        vp = VisaProject.query.filter_by(ref_id=ref.id).first()
        if not vp or not vp.visa_type:
            print(f"  ref {ref.id} ({ref.ref_number}) 无关联签证项目或缺签证类型, 跳过")
            continue
        vt = VisaTypes.query.filter_by(visa_type=vp.visa_type).first()
        country_en = (vt.country.country_name_EN if vt and vt.country else '') or (vp.country or '')
        vt_en = (getattr(vt, 'visa_type_en', None) or '') if vt else ''
        new_name = f"{country_en} {vt_en or vp.visa_type}".strip()
        if not new_name:
            print(f"  ref {ref.id} 无法生成名称, 跳过")
            continue
        # 保留原名称中 "VISA" 之后的附加信息（如 "| 27DEC"）
        desc = ref.description or ''
        idx = desc.upper().find('VISA')
        suffix = desc[idx + 4:].strip() if idx != -1 else ''
        if suffix:
            new_name = f"{new_name} {suffix}"
        print(f"  ref {ref.id} ({ref.ref_number}): '{ref.description}' -> '{new_name}'")
        if do_fix:
            ref.description = new_name
            ref.detailed_description = new_name
            # 同步把国家补到 VisaProject（编辑页读取处）
            if country_en and not (vp.country or '').strip():
                vp.country = country_en.upper()
            fixed += 1

    if do_fix:
        db.session.commit()
        print(f"\n完成：已修正 {fixed} 个签证REF名称。")
    else:
        print("\n[仅报告] 未修改。加 --fix 执行。")
