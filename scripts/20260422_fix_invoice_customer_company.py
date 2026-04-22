"""
修复历史发票的 customer_company 快照字段
将 project_invoices.customer_company 对齐到项目当前归属公司 customer_companies.company_name

背景: 早期项目归属"个人"时创建了发票, 后期项目改挂到具体公司,
      但 project_invoices.customer_company 是创建时的快照, 没有跟着更新,
      导致发票列表按公司关键字搜索时漏掉这些发票

默认范围: 仅修 status='confirmed' 且 payment_status <> 'paid' 的发票,
         这批是真正影响业务/搜索的, 已付款 / 已作废的默认不动
         (保留历史凭证, 因代码层的搜索改动已能覆盖这些场景)

运行方式:
    python scripts/20260422_fix_invoice_customer_company.py                       # 预览 (只看 confirmed+未付款)
    python scripts/20260422_fix_invoice_customer_company.py --hid H1187           # 预览单个项目
    python scripts/20260422_fix_invoice_customer_company.py --execute             # 执行 (默认范围)
    python scripts/20260422_fix_invoice_customer_company.py --include-cancelled   # 连同 cancelled 一起
    python scripts/20260422_fix_invoice_customer_company.py --include-paid        # (慎用) 连同已付款一起
    python scripts/20260422_fix_invoice_customer_company.py --all                 # 不管状态全改
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import collate

app = create_app()

# project_invoices.customer_company 与 customer_companies.company_name 的 collation
# 可能不一致 (MySQL 8 常见 utf8mb4_unicode_ci vs utf8mb4_0900_ai_ci 冲突),
# 显式 COLLATE 统一为 utf8mb4_unicode_ci 再比较
_COLLATION = 'utf8mb4_unicode_ci'


def fix_invoice_customer_company(dry_run=True, only_hid=None,
                                  include_cancelled=False, include_paid=False, include_all=False):
    from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
    from App_new.business.projects.models.invoice import ProjectInvoice

    prefix = '[DRY RUN] ' if dry_run else ''
    print(f"{prefix}开始检查 project_invoices.customer_company 与项目归属公司的一致性...")
    if only_hid:
        print(f"仅处理项目: {only_hid}")

    # 范围说明
    if include_all:
        print("范围: 所有状态的发票 (包括已付款 / 已作废)")
    else:
        scopes = ["confirmed + 未付款"]
        if include_cancelled:
            scopes.append("cancelled")
        if include_paid:
            scopes.append("已付款")
        print(f"范围: {' + '.join(scopes)}")
    print('-' * 100)

    query = db.session.query(
        ProjectInvoice,
        ProjectHeader.hid.label('hid'),
        CustomerCompany.company_name.label('header_company_name')
    ).join(
        ProjectHeader, ProjectInvoice.header_id == ProjectHeader.id
    ).join(
        CustomerCompany, ProjectHeader.company_id == CustomerCompany.id
    ).filter(
        CustomerCompany.company_name.isnot(None),
        db.or_(
            ProjectInvoice.customer_company.is_(None),
            ProjectInvoice.customer_company != collate(CustomerCompany.company_name, _COLLATION)
        )
    )

    # 状态范围过滤
    if not include_all:
        status_conditions = [
            db.and_(
                ProjectInvoice.status == 'confirmed',
                ProjectInvoice.payment_status != 'paid'
            )
        ]
        if include_cancelled:
            status_conditions.append(ProjectInvoice.status == 'cancelled')
        if include_paid:
            status_conditions.append(ProjectInvoice.payment_status == 'paid')
        query = query.filter(db.or_(*status_conditions))

    if only_hid:
        query = query.filter(ProjectHeader.hid == only_hid)

    rows = query.order_by(ProjectHeader.hid, ProjectInvoice.invoice_date).all()

    if not rows:
        print('没有发现需要修复的数据')
        return 0

    print(f"{'HID':<10} {'INV#':<12} {'STATUS':<12} {'PAY':<10} {'OLD customer_company':<35} {'NEW (header company)':<35}")
    print('-' * 100)

    count_confirmed_unpaid = 0
    count_cancelled = 0
    count_paid = 0

    for inv, hid, header_company_name in rows:
        old_value = inv.customer_company if inv.customer_company is not None else '<NULL>'
        print(
            f"{hid:<10} {inv.invoice_number:<12} {inv.status or '':<12} "
            f"{inv.payment_status or '':<10} {old_value[:34]:<35} {header_company_name[:34]:<35}"
        )

        if inv.status == 'confirmed' and inv.payment_status != 'paid':
            count_confirmed_unpaid += 1
        elif inv.status == 'cancelled':
            count_cancelled += 1
        elif inv.payment_status == 'paid':
            count_paid += 1

        if not dry_run:
            inv.customer_company = header_company_name

    print('-' * 100)
    print(
        f"总计 {len(rows)} 张需要修正 "
        f"(confirmed+未付款 {count_confirmed_unpaid}, cancelled {count_cancelled}, 已付款 {count_paid})"
    )

    if not dry_run:
        db.session.commit()
        print(f"已提交 {len(rows)} 张发票的 customer_company 更新")
    else:
        print('\n这是预览模式, 未实际修改数据')
        print('如需执行更新, 请加 --execute 参数')

    return len(rows)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='修复发票 customer_company 快照字段')
    parser.add_argument('--execute', action='store_true', help='执行更新 (默认只预览)')
    parser.add_argument('--hid', type=str, default=None, help='只修指定项目, 如 H1187')
    parser.add_argument('--include-cancelled', action='store_true', help='一并修 cancelled 状态的发票')
    parser.add_argument('--include-paid', action='store_true', help='(慎用) 一并修已付款发票, 会改历史凭证')
    parser.add_argument('--all', action='store_true', help='不管状态全改 (等同 --include-cancelled --include-paid)')
    args = parser.parse_args()

    dry_run = not args.execute

    with app.app_context():
        if not dry_run:
            if args.include_paid or args.all:
                print("警告: 将修改已付款发票的 customer_company, 这会改动历史凭证")
            confirm = input("确定要执行更新吗? 输入 'yes' 确认: ")
            if confirm.lower() != 'yes':
                print("已取消")
                sys.exit(0)

        fix_invoice_customer_company(
            dry_run=dry_run,
            only_hid=args.hid,
            include_cancelled=args.include_cancelled,
            include_paid=args.include_paid,
            include_all=args.all,
        )
