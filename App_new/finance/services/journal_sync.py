# -*- coding: utf-8 -*-
"""
业务单据与日记账分录的同步

单据作废或删除时，当初生成的分录必须一并冲销，否则账上会留下永远不会被
发现的虚增：FY2026 实测有 188 张已作废发票、78 张已删除发票、49 笔已删除
收款的分录还挂在账上，合计虚增收入 3.5 万、虚增银行 2 万。

统一走冲销而不是删除分录：
- 冲销留痕（原分录标 reversed + 生成借贷相反的新分录），审计能追溯
- 删除就查无对证，也破坏了分录编号的连续性

report 层面两条一起计入、借贷相反自动抵消，净效果为 0。
"""

import logging

from App_new.exts import db
from App_new.finance.models.journal_entry import JournalEntry

logger = logging.getLogger(__name__)

# 单据类型 -> JournalEntry.source_type
SOURCE_TYPES = ('invoice', 'receipt', 'eo', 'operating_expense')


def reverse_entries_for(source_type, source_id, user=None, reason=None):
    """冲销某张单据对应的全部已过账分录

    返回 (冲销条数, 冲销金额)。没有分录时返回 (0, 0)，不算失败。

    刻意不抛异常：作废单据这个动作本身不该因为分录问题而失败——账目
    可以事后补救，但用户点了作废却报错、单据还是原状，会更让人困惑。
    出问题记 warning，由对账检查页兜底暴露。
    """
    if source_type not in SOURCE_TYPES:
        raise ValueError(f'不支持的单据类型: {source_type}')

    entries = JournalEntry.query.filter(
        JournalEntry.source_type == source_type,
        JournalEntry.source_id == source_id,
        JournalEntry.status == 'posted',
    ).all()

    count, amount = 0, 0
    for entry in entries:
        # 冲销分录本身也是 source_type=invoice/posted，不能再冲一次，
        # 否则会无限套娃。它的 source_number 带 REV- 前缀，据此识别。
        if entry.source_number and str(entry.source_number).startswith('REV-'):
            continue
        try:
            reversal = entry.reverse(user=user)
            if reversal:
                if reason:
                    reversal.remarks = f'{reversal.remarks or ""}｜{reason}'.strip('｜')
                db.session.add(reversal)
                count += 1
                amount += float(entry.total_amount or 0)
        except Exception as exc:
            logger.warning(
                f'冲销分录失败 {source_type}#{source_id} {entry.entry_number}: {exc}')

    if count:
        logger.info(f'冲销 {source_type}#{source_id} 的 {count} 条分录，金额 {amount:.2f}')
    return count, amount


def has_posted_entries(source_type, source_id):
    """该单据是否还有未冲销的已过账分录

    删除单据前用它拦一道：分录还在就先冲销，不然分录会变成找不到来源的
    孤儿，连追溯都做不到。
    """
    # 必须排除冲销分录自己：它也是 posted、也挂在同一张单据上，
    # 不排除的话冲销完再查还是 True，这个函数就永远返回真了。
    return db.session.query(
        JournalEntry.query.filter(
            JournalEntry.source_type == source_type,
            JournalEntry.source_id == source_id,
            JournalEntry.status == 'posted',
            db.or_(JournalEntry.source_number.is_(None),
                   ~JournalEntry.source_number.like('REV-%')),
        ).exists()
    ).scalar()


def resync_invoice_entry(invoice, user=None, reason=None):
    """发票金额改动后重新生成分录：冲销旧的 + 按新金额建新的

    用"冲销+重建"而不是就地改分录金额：
    - 就地改要同时改两条明细行，改错一边借贷就不平了
    - 冲销留痕，能看出金额什么时候被改的、改了多少
    - 和作废/删除走同一套机制，行为一致

    返回 (冲销条数, 是否新建)。发票已作废则只冲销不重建。
    """
    reversed_count, _ = reverse_entries_for('invoice', invoice.id, user=user, reason=reason)

    if invoice.status != 'confirmed' or not invoice.amount:
        return reversed_count, False

    entry = JournalEntry.create_from_invoice(invoice, user=user)
    if not entry or not entry.lines:
        return reversed_count, False
    if not entry.is_balanced:
        logger.warning(f'发票 {invoice.invoice_number} 重建分录借贷不平，已跳过')
        return reversed_count, False

    if reason:
        entry.remarks = reason
    db.session.add(entry)
    return reversed_count, True
