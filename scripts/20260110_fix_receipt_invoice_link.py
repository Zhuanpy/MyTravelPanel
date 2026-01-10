# -*- coding: utf-8 -*-
"""
修复收款记录与发票关联脚本

问题：部分收款记录通过 extra_info.distribution 分配给了 REF，
但 invoice_id 字段为空，导致发票的 paid_amount 未正确更新。

解决方案：
1. 查找所有 invoice_id 为空但有 extra_info.distribution 的收款记录
2. 根据分配的 REF，找到对应的发票
3. 创建 receipt_invoice_allocations 记录，将收款关联到发票
4. 更新发票的 paid_amount 和 payment_status

使用方法:
    python scripts/20260110_fix_receipt_invoice_link.py           # 预览模式
    python scripts/20260110_fix_receipt_invoice_link.py --execute  # 执行模式
"""

import sys
import os
import json
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    """从 Flask 配置中获取数据库配置"""
    try:
        from App_new.config import Config
        # 解析 SQLALCHEMY_DATABASE_URI
        uri = Config.SQLALCHEMY_DATABASE_URI
        # mysql+pymysql://user:password@host:port/database
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)'
        match = re.match(pattern, uri)
        if match:
            return {
                'host': match.group(3),
                'port': int(match.group(4)),
                'user': match.group(1),
                'password': match.group(2),
                'database': match.group(5),
                'charset': 'utf8mb4'
            }
    except Exception as e:
        print(f"警告: 无法从 Flask 配置读取数据库信息: {e}")

    # 默认配置（本地开发环境）
    return {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '***REMOVED***',
        'database': 'travelindustry',
        'charset': 'utf8mb4'
    }


def get_connection():
    """获取数据库连接"""
    db_config = get_db_config()
    try:
        import pymysql
        return pymysql.connect(**db_config)
    except ImportError:
        try:
            import mysql.connector
            config = db_config.copy()
            config['db'] = config.pop('database')
            return mysql.connector.connect(**config)
        except ImportError:
            print("错误: 需要安装 pymysql 或 mysql-connector-python")
            print("请运行: pip install pymysql")
            sys.exit(1)


def find_unlinked_receipts(cursor):
    """查找未关联发票但有分配信息的收款记录"""
    cursor.execute("""
        SELECT id, receipt_number, header_id, amount, extra_info
        FROM project_receipts
        WHERE invoice_id IS NULL
          AND extra_info IS NOT NULL
          AND extra_info != ''
          AND status = 'confirmed'
        ORDER BY id
    """)

    unlinked = []
    for row in cursor.fetchall():
        receipt_id, receipt_number, header_id, amount, extra_info = row

        try:
            info = json.loads(extra_info)
            if 'distribution' in info and info['distribution']:
                # 提取分配的 REF ID 列表
                ref_ids = [d.get('ref_id') for d in info['distribution'] if d.get('ref_id')]
                if ref_ids:
                    unlinked.append({
                        'receipt_id': receipt_id,
                        'receipt_number': receipt_number,
                        'header_id': header_id,
                        'amount': float(amount) if amount else 0,
                        'distribution': info['distribution'],
                        'ref_ids': ref_ids
                    })
        except (json.JSONDecodeError, TypeError):
            pass

    return unlinked


def find_invoices_for_refs(cursor, ref_ids, header_id):
    """根据 REF ID 列表查找关联的发票"""
    if not ref_ids:
        return []

    # 查找包含这些 REF 的发票
    cursor.execute("""
        SELECT id, invoice_number, ref_ids, amount, paid_amount, payment_status
        FROM project_invoices
        WHERE header_id = %s AND status != 'cancelled' AND ref_ids IS NOT NULL
    """, (header_id,))

    matched_invoices = []
    for row in cursor.fetchall():
        invoice_id, invoice_number, invoice_ref_ids, amount, paid_amount, payment_status = row

        try:
            invoice_refs = json.loads(invoice_ref_ids)
            # 检查发票的 ref_ids 是否包含我们要找的 ref_id
            for ref_id in ref_ids:
                if ref_id in invoice_refs or str(ref_id) in invoice_refs:
                    matched_invoices.append({
                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                        'ref_ids': invoice_refs,
                        'amount': float(amount) if amount else 0,
                        'paid_amount': float(paid_amount) if paid_amount else 0,
                        'payment_status': payment_status,
                        'matched_ref_id': ref_id
                    })
                    break  # 一个发票只匹配一次
        except (json.JSONDecodeError, TypeError):
            pass

    return matched_invoices


def check_existing_allocation(cursor, receipt_id, invoice_id):
    """检查是否已存在分配记录"""
    cursor.execute("""
        SELECT id FROM receipt_invoice_allocations
        WHERE receipt_id = %s AND invoice_id = %s
    """, (receipt_id, invoice_id))
    return cursor.fetchone() is not None


def determine_payment_status(amount, paid_amount):
    """根据金额确定付款状态"""
    if amount <= 0:
        return 'paid'
    if paid_amount >= amount:
        return 'paid'
    elif paid_amount > 0:
        return 'partial_paid'
    else:
        return 'unpaid'


def calculate_invoice_total_allocated(cursor, invoice_id):
    """计算发票从分配表获得的总已付金额"""
    cursor.execute("""
        SELECT COALESCE(SUM(ria.allocated_amount), 0)
        FROM receipt_invoice_allocations ria
        JOIN project_receipts pr ON ria.receipt_id = pr.id
        WHERE ria.invoice_id = %s AND pr.status = 'confirmed'
    """, (invoice_id,))
    result = cursor.fetchone()
    return float(result[0]) if result and result[0] else 0


def fix_receipt_invoice_links(execute=False):
    """修复收款记录与发票的关联"""
    print("=" * 80)
    print("修复收款记录与发票关联脚本")
    print("=" * 80)
    print(f"模式: {'执行模式' if execute else '预览模式（不修改数据）'}")
    print()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. 查找未关联的收款记录
        unlinked_receipts = find_unlinked_receipts(cursor)
        print(f"找到 {len(unlinked_receipts)} 条未关联发票但有分配信息的收款记录")
        print()

        if not unlinked_receipts:
            print("没有需要修复的记录。")
            return 0

        # 2. 分析每条收款记录，找到对应的发票
        fixes_needed = []
        # 用于追踪每个发票将获得的新增分配金额
        invoice_new_allocations = {}

        for receipt in unlinked_receipts:
            invoices = find_invoices_for_refs(cursor, receipt['ref_ids'], receipt['header_id'])

            for invoice in invoices:
                # 检查是否已存在分配
                if not check_existing_allocation(cursor, receipt['receipt_id'], invoice['invoice_id']):
                    # 计算应该分配的金额（基于 REF 分配）
                    allocated_amount = 0
                    for dist in receipt['distribution']:
                        ref_id = dist.get('ref_id')
                        if ref_id and (ref_id in invoice['ref_ids'] or str(ref_id) in invoice['ref_ids']):
                            allocated_amount += dist.get('amount', 0)

                    if allocated_amount > 0:
                        invoice_id = invoice['invoice_id']

                        # 累计该发票的新增分配
                        if invoice_id not in invoice_new_allocations:
                            invoice_new_allocations[invoice_id] = {
                                'invoice_number': invoice['invoice_number'],
                                'invoice_amount': invoice['amount'],
                                'current_allocated': calculate_invoice_total_allocated(cursor, invoice_id),
                                'new_allocations': []
                            }

                        invoice_new_allocations[invoice_id]['new_allocations'].append({
                            'receipt_id': receipt['receipt_id'],
                            'receipt_number': receipt['receipt_number'],
                            'receipt_amount': receipt['amount'],
                            'allocated_amount': allocated_amount
                        })

                        fixes_needed.append({
                            'receipt_id': receipt['receipt_id'],
                            'receipt_number': receipt['receipt_number'],
                            'receipt_amount': receipt['amount'],
                            'invoice_id': invoice_id,
                            'invoice_number': invoice['invoice_number'],
                            'invoice_amount': invoice['amount'],
                            'allocated_amount': allocated_amount
                        })

        # 3. 显示修复计划
        if fixes_needed:
            print(f"需要创建 {len(fixes_needed)} 条分配记录，涉及 {len(invoice_new_allocations)} 张发票")
            print("-" * 100)
            print(f"{'收款单号':<20} {'收款金额':>12} {'发票号':<20} {'发票金额':>12} {'分配金额':>12}")
            print("-" * 100)

            for fix in fixes_needed:
                print(f"{fix['receipt_number']:<20} {fix['receipt_amount']:>12.2f} "
                      f"{fix['invoice_number']:<20} {fix['invoice_amount']:>12.2f} "
                      f"{fix['allocated_amount']:>12.2f}")

            print("-" * 100)
            print()

            # 显示每张发票的汇总
            print("发票付款状态更新预览:")
            print("-" * 100)
            print(f"{'发票号':<20} {'发票金额':>12} {'当前已分配':>12} {'新增分配':>12} {'新已付':>12} {'新状态':<15}")
            print("-" * 100)

            for invoice_id, info in invoice_new_allocations.items():
                new_alloc_total = sum(a['allocated_amount'] for a in info['new_allocations'])
                new_paid = info['current_allocated'] + new_alloc_total
                # 限制不超过发票金额
                new_paid = min(new_paid, info['invoice_amount'])
                new_status = determine_payment_status(info['invoice_amount'], new_paid)

                print(f"{info['invoice_number']:<20} {info['invoice_amount']:>12.2f} "
                      f"{info['current_allocated']:>12.2f} {new_alloc_total:>12.2f} "
                      f"{new_paid:>12.2f} {new_status:<15}")

            print("-" * 100)
            print()

            if execute:
                print("正在执行修复...")

                # 创建分配记录
                for fix in fixes_needed:
                    cursor.execute("""
                        INSERT INTO receipt_invoice_allocations
                        (receipt_id, invoice_id, allocated_amount, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (fix['receipt_id'], fix['invoice_id'], fix['allocated_amount']))

                # 更新每张发票的已付金额和状态
                for invoice_id, info in invoice_new_allocations.items():
                    # 重新计算该发票的总分配金额
                    new_paid = calculate_invoice_total_allocated(cursor, invoice_id)
                    # 加上刚才插入的分配
                    new_alloc_total = sum(a['allocated_amount'] for a in info['new_allocations'])
                    new_paid += new_alloc_total
                    # 限制不超过发票金额
                    new_paid = min(new_paid, info['invoice_amount'])
                    new_status = determine_payment_status(info['invoice_amount'], new_paid)

                    cursor.execute("""
                        UPDATE project_invoices
                        SET paid_amount = %s, payment_status = %s
                        WHERE id = %s
                    """, (new_paid, new_status, invoice_id))

                conn.commit()
                print(f"成功创建 {len(fixes_needed)} 条分配记录")
                print(f"成功更新 {len(invoice_new_allocations)} 张发票的付款状态")
            else:
                print("预览模式，未执行修复。")
                print("如需执行修复，请运行: py scripts/20260110_fix_receipt_invoice_link.py --execute")
        else:
            print("没有需要创建的分配记录。")

        print()
        print("=" * 80)
        return len(fixes_needed)

    except Exception as e:
        conn.rollback()
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        cursor.close()
        conn.close()


def main():
    """主函数"""
    execute = '--execute' in sys.argv or '-e' in sys.argv
    result = fix_receipt_invoice_links(execute=execute)
    return 0 if result >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
