"""重复发票诊断（只读）

用途: 同一个 HID 出现两张金额/日期都一样的发票，判断到底是
  - 重复点击生成的（两张 ref_ids 相同）
  - 还是其中一张没挂 REF / 挂到别的 REF（所以项目详情页的 Invoice 列只显示一张）
  - 还是已被取消（status=cancelled，SOA 列表不会显示）

运行方式:
    python scripts/tools/20260731_diagnose_duplicate_invoice.py --header 3291
    python scripts/tools/20260731_diagnose_duplicate_invoice.py --inv 12265 12266
    python scripts/tools/20260731_diagnose_duplicate_invoice.py --scan       # 全库扫可疑重复
"""
import sys
import os
import json
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef


def parse_ref_ids(raw):
    """把 ref_ids 原样解析出来，同时保留元素类型（int / str 混用是重复发票的成因之一）"""
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else [val]
    except (json.JSONDecodeError, TypeError):
        return ['<解析失败: %r>' % raw]


def dump_invoice(inv):
    print('--- 发票 %s (id=%s) ---' % (inv.invoice_number, inv.id))
    print('   状态          : %s   付款状态: %s   已付: %s' % (inv.status, inv.payment_status, inv.paid_amount))
    print('   金额          : %s %s' % (inv.currency, inv.amount))
    print('   发票日期      : %s' % inv.invoice_date)
    print('   项目 header_id: %s' % inv.header_id)
    print('   客户          : %s / %s' % (inv.customer_name, inv.customer_company))
    print('   创建时间      : %s   创建人: %s' % (inv.created_at, inv.created_by))
    print('   备注          : %s' % (inv.remarks or ''))

    ref_ids = parse_ref_ids(inv.ref_ids)
    print('   ref_ids 原始值: %r' % inv.ref_ids)
    print('   ref_ids 解析后: %s  (元素类型: %s)'
          % (ref_ids, [type(x).__name__ for x in ref_ids]))
    for rid in ref_ids:
        try:
            ref = ProjectRef.query.get(int(rid))
        except (TypeError, ValueError):
            ref = None
        if ref:
            print('      -> REF %s (id=%s) %s' % (ref.ref_number, ref.id, ref.description))
        else:
            print('      -> ❗ref id=%r 已不存在（REF 被删过？）' % rid)
    if not ref_ids:
        print('      -> ❗没有关联任何 REF：项目详情页的 Invoice 列不会显示这张发票')

    items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
    print('   发票明细      : %s 条' % len(items))
    for it in items:
        print('      item id=%s ref_id=%s %s  %s' % (it.id, it.ref_id, it.description, it.total_price))

    try:
        allocs = inv.receipt_allocations
        print('   收款分配      : %s 笔' % len(allocs))
    except Exception as e:
        db.session.rollback()
        print('   收款分配      : 查询失败 %s' % e)

    try:
        from App_new.finance.models.journal_entry import JournalEntry
        entries = JournalEntry.query.filter(
            JournalEntry.source_type == 'invoice',
            JournalEntry.source_id == inv.id).all()
        print('   日记账分录    : %s' % ', '.join('%s(%s)' % (e.entry_number, e.status) for e in entries)
              or '   日记账分录    : 无')
        if inv.status == 'cancelled' and any(e.status == 'posted' for e in entries):
            print('      ❗发票已取消但日记账还是 posted —— 账上应收没冲掉')
    except Exception as e:
        db.session.rollback()
        print('   日记账分录    : 查询失败 %s' % e)
    print('')


def compare(invoices):
    """判断这几张发票之间是什么关系"""
    print('=== 判定 ===')
    live = [i for i in invoices if i.status != 'cancelled']
    print('  有效(非cancelled)发票: %s 张 -> %s'
          % (len(live), ', '.join(i.invoice_number for i in live)))
    cancelled = [i for i in invoices if i.status == 'cancelled']
    if cancelled:
        print('  已取消: %s' % ', '.join(i.invoice_number for i in cancelled))

    sets = {}
    for i in invoices:
        sets[i.invoice_number] = set(str(x) for x in parse_ref_ids(i.ref_ids))
    keys = list(sets)
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            sa, sb = sets[keys[a]], sets[keys[b]]
            if sa and sa == sb:
                print('  ❗%s 与 %s 关联的 REF 完全相同 -> 典型的重复生成（重复点击/重复提交）'
                      % (keys[a], keys[b]))
            elif not sa or not sb:
                empty = keys[a] if not sa else keys[b]
                print('  ❗%s 没有关联任何 REF -> 不是重复点击，是用没选 REF 的路径单独开的一张'
                      % empty)
            elif sa & sb:
                print('  ❗%s 与 %s 关联的 REF 部分重叠: %s' % (keys[a], keys[b], sa & sb))
            else:
                print('  %s 与 %s 关联的是不同 REF，属于正常的多张发票' % (keys[a], keys[b]))
    print('')
    print('  处置建议: 作废多余的那张请用「按发票号作废」(/projects/invoice/void)，')
    print('           它会同时冲销日记账；详情页的 /<id>/cancel 只改状态、不冲日记账。')


def scan():
    print('=== 全库扫描：同一 REF 挂了多张有效发票 ===')
    ref_map = defaultdict(list)
    invoices = ProjectInvoice.query.filter(ProjectInvoice.status != 'cancelled').all()
    no_ref = []
    for inv in invoices:
        ids = parse_ref_ids(inv.ref_ids)
        if not ids:
            no_ref.append(inv)
        for rid in ids:
            ref_map[str(rid)].append(inv)

    dup = {k: v for k, v in ref_map.items() if len(v) > 1}
    if not dup:
        print('  ✅ 没有一个 REF 挂了多张有效发票')
    for rid, invs in sorted(dup.items(), key=lambda kv: -len(kv[1])):
        ref = ProjectRef.query.get(int(rid)) if str(rid).isdigit() else None
        print('  REF %s (%s): %s' % (rid, ref.ref_number if ref else '已删除',
                                     ', '.join('%s[%s]' % (i.invoice_number, i.amount) for i in invs)))

    print('')
    print('=== 有效但没关联任何 REF 的发票: %s 张 ===' % len(no_ref))
    for inv in no_ref[:50]:
        print('  %s  header_id=%s  %s %s  %s'
              % (inv.invoice_number, inv.header_id, inv.currency, inv.amount, inv.invoice_date))
    if len(no_ref) > 50:
        print('  ...（只显示前 50 条）')

    print('')
    print('=== ref_ids 里存成字符串的发票（会让"未开票REF"判断失效，导致重复生成）===')
    bad = [i for i in invoices if any(isinstance(x, str) for x in parse_ref_ids(i.ref_ids))]
    print('  %s 张: %s' % (len(bad), ', '.join(i.invoice_number for i in bad[:30])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--header', type=int, help='按项目 header_id 列出全部发票')
    parser.add_argument('--inv', nargs='+', help='按发票号列出（可多个）')
    parser.add_argument('--scan', action='store_true', help='全库扫描可疑重复')
    args = parser.parse_args()

    if not any([args.header, args.inv, args.scan]):
        parser.error('请给出 --header / --inv / --scan 之一')

    app = create_app()
    with app.app_context():
        if args.scan:
            scan()
            return

        if args.header:
            header = ProjectHeader.query.get(args.header)
            if not header:
                print('❌ 项目 %s 不存在' % args.header)
                return
            print('=== 项目 %s  HID=%s  %s ===' % (header.id, header.hid, header.desc))
            invoices = ProjectInvoice.query.filter_by(header_id=args.header) \
                .order_by(ProjectInvoice.id).all()
            print('共 %s 张发票\n' % len(invoices))
        else:
            invoices = ProjectInvoice.query.filter(
                ProjectInvoice.invoice_number.in_(args.inv)).order_by(ProjectInvoice.id).all()
            found = {i.invoice_number for i in invoices}
            for n in args.inv:
                if n not in found:
                    print('❌ 未找到发票号 %s' % n)
            print('')

        for inv in invoices:
            dump_invoice(inv)
        if len(invoices) > 1:
            compare(invoices)


if __name__ == '__main__':
    main()
