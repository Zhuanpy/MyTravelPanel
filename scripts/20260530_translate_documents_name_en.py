# -*- coding: utf-8 -*-
"""
数据脚本：将 visa_documents_list 现有中文文档名称翻译为英文，写入 name_en 字段。

使用内置的中英对照表（VISA 文档常用术语，面向客户用英文）。
- 默认只填充 name_en 为空的记录；加 --force 覆盖所有记录。
- 未在对照表中的名称会被列出，可手动补充 TRANSLATIONS 后重跑。

运行方式:
  python scripts/20260530_translate_documents_name_en.py          # 仅填充空白
  python scripts/20260530_translate_documents_name_en.py --force  # 覆盖全部
  python scripts/20260530_translate_documents_name_en.py --dry    # 预览不写库
提示：若控制台报 UnicodeEncodeError，先执行 $env:PYTHONIOENCODING='utf-8'
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

# 中文文档名称 -> 英文（面向客户的英文表述）
TRANSLATIONS = {
    '护照原件': 'Passport (Original)',
    '护照首页': 'Passport Bio Page',
    '护照空白页': 'Passport Blank Page',
    '旧签证页（如有）': 'Old Visa Page (if any)',
    '照片': 'Photo',
    '2寸白底照片': '2-inch White Background Photo',
    '近3个月银行流水': 'Last 3 Months Bank Statement',
    '公司ACRA': 'Company ACRA',
    '雇主银行流水': 'Employer Bank Statement',
    '往返机票单': 'Round-trip Flight Ticket',
    '酒店订单': 'Hotel Booking',
    '旅游保险': 'Travel Insurance',
    '工作准证': 'Work Permit',
    '工作证二维码扫码': 'Work Pass QR Code Scan',
    'IPA LETTER': 'IPA Letter',
    '公司在职证明': 'Employment Certificate',
    '雇主护照 & IC': 'Employer Passport & IC',
    '雇主解释担保信': 'Employer Explanation / Guarantee Letter',
    '学校在读证明': 'Student Enrollment Certificate',
    '担保信': 'Guarantee Letter',
    '被照顾人护照 & 出生证明': 'Care Recipient Passport & Birth Certificate',
    '关系证明': 'Proof of Relationship',
    '结婚证明': 'Marriage Certificate',
    '出生证明及翻译件': 'Birth Certificate & Translation',
    '赞助人护照 & IC': 'Sponsor Passport & IC',
    '赞助关系证明': 'Proof of Sponsorship Relationship',
    '申请表格': 'Application Form',
    '新加坡IC': 'Singapore IC',
    'Re-entry permit': 'Re-entry Permit',
    '结婚证明原件': 'Marriage Certificate (Original)',
    '结婚证明复印件': 'Marriage Certificate (Copy)',
    '近2个月银行流水': 'Last 2 Months Bank Statement',
    '近6个月银行流水': 'Last 6 Months Bank Statement',
    '如需赞助': 'If Sponsorship Required',
    '公司ACRA（自雇人士）': 'Company ACRA (Self-employed)',
    '中国身份证': 'China ID Card',
    '中国户口本': 'China Household Register (Hukou)',
    '身份证照片': 'ID Card Photo',
    '出生证明': 'Birth Certificate',
    '学历证明': 'Education Certificate',
    '银行对账单': 'Bank Statement',
    '签证申请表': 'Visa Application Form',
    '授权信': 'Authorization Letter',
    '旅行计划': 'Travel Itinerary',
    '白底照片5cm*5cm': 'White Background Photo 5cm*5cm',
    '出生公证': 'Notarized Birth Certificate',
    '海牙公证': 'Hague Apostille',
    '海基会公证': 'SEF Notarization',
    'DS160表格': 'DS-160 Form',
    '预约信': 'Appointment Letter',
    '近3个月薪水单': 'Last 3 Months Payslip',
    '赞助信': 'Sponsorship Letter',
    '历史旅行记录': 'Travel History',
    '出入境证明': 'Entry-Exit Record',
    'IRAS （新加坡税单）': 'IRAS (Singapore Tax Statement)',
    '近3个月银行流水单（如银行流水无薪水进账显示，需提供薪水单）':
        'Last 3 Months Bank Statement (provide payslip if salary not shown)',
    '校园卡': 'Campus Card',
    '美国签证（如有）': 'US Visa (if any)',
}

app = create_app()

with app.app_context():
    from App_new.business.visa.models.Visamodels import VisaDocumentsList

    args = set(sys.argv[1:])
    force = '--force' in args
    dry = '--dry' in args

    rows = VisaDocumentsList.query.order_by(VisaDocumentsList.id.asc()).all()

    updated = 0
    skipped = 0
    missing = []

    for r in rows:
        en = TRANSLATIONS.get(r.name)
        if en is None:
            missing.append(r.name)
            continue
        # 已有英文且非强制覆盖则跳过
        if r.name_en and r.name_en.strip() and not force:
            skipped += 1
            continue
        print("[{}] {}  ->  {}".format(r.id, r.name, en))
        if not dry:
            r.name_en = en
        updated += 1

    if not dry:
        db.session.commit()

    print("\n" + "=" * 60)
    print("更新 {} 条 | 跳过(已有英文) {} 条 | 未匹配 {} 条 {}".format(
        updated, skipped, len(missing), '(dry-run 未写库)' if dry else ''))
    if missing:
        print("\n以下名称未在对照表中，请手动补充 TRANSLATIONS 后重跑：")
        for m in missing:
            print("  - {}".format(m))
