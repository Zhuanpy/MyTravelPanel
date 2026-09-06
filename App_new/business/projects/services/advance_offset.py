# -*- coding: utf-8 -*-
"""客户预收款抵扣

业务流程是「先收钱、后开票」：客户对某个项目先付一笔钱（那时还没有发票），
后续项目开出发票，从这笔预收里抵扣。

    收预收款   借 银行     / 贷 预收账款(2200)
    开发票     借 应收账款 / 贷 销售收入
    抵扣       借 预收账款 / 贷 应收账款(1100)    <- 本模块

抵扣按收款日期先进先出，跨发票、跨收款单都支持部分抵扣。核销记录复用现有的
receipt_invoice_allocations 表 —— 它本来就是「收款 -> 发票」的多对多分配表，
预收核销就是往里加一条，不需要新表。
"""

from decimal import Decimal

from App_new.exts import db
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation


def get_advance_balance(header_id):
    """该项目当前可用的预收余额"""
    total = Decimal('0')
    for r in available_advances(header_id):
        total += r.advance_balance
    return total


def available_advances(header_id):
    """该项目下还有余额的预收款，按收款日期先进先出

    先收的先用完，符合客户「这笔钱先扣」的直觉，也让预收账龄不会一直挂着。
    """
    receipts = ProjectReceipt.query.filter_by(
        header_id=header_id, receipt_type='advance', status='confirmed'
    ).order_by(ProjectReceipt.payment_date.asc(), ProjectReceipt.id.asc()).all()
    return [r for r in receipts if r.advance_balance > 0]


def offset_invoice(invoice, user=None, max_amount=None):
    """用该项目的预收款抵扣一张发票

    返回 (抵扣总额, [生成的分录, ...])。没有预收余额时返回 (Decimal('0'), [])。

    调用方负责 commit —— 本函数只 add 到 session，方便和开票放在同一个事务里，
    要么一起成功要么一起回滚。
    """
    from App_new.finance.models.journal_entry import JournalEntry

    outstanding = _invoice_outstanding(invoice)
    if max_amount is not None:
        outstanding = min(outstanding, Decimal(str(max_amount)))
    if outstanding <= 0:
        return Decimal('0'), []

    offset_total = Decimal('0')
    entries = []

    for receipt in available_advances(invoice.header_id):
        if outstanding <= 0:
            break
        take = min(receipt.advance_balance, outstanding)
        if take <= 0:
            continue

        # 核销记录：同一对「收款-发票」只能有一条（表上有唯一约束），
        # 二次抵扣时累加而不是新插一条
        alloc = ReceiptInvoiceAllocation.query.filter_by(
            receipt_id=receipt.id, invoice_id=invoice.id).first()
        if alloc:
            alloc.allocated_amount = (alloc.allocated_amount or Decimal('0')) + take
        else:
            db.session.add(ReceiptInvoiceAllocation(
                receipt_id=receipt.id, invoice_id=invoice.id, allocated_amount=take))

        entry = JournalEntry.create_from_advance_offset(receipt, invoice, take, user=user)
        if entry and entry.lines:
            db.session.add(entry)
            entries.append(entry)

        offset_total += take
        outstanding -= take

    if offset_total > 0:
        db.session.flush()
        invoice.paid_amount = (invoice.paid_amount or Decimal('0')) + offset_total
        if hasattr(invoice, 'update_payment_status'):
            invoice.update_payment_status()

    return offset_total, entries


def _invoice_outstanding(invoice):
    """发票未收金额"""
    amount = Decimal(str(invoice.amount or 0))
    paid = Decimal(str(invoice.paid_amount or 0))
    return max(amount - paid, Decimal('0'))
