# -*- coding: utf-8 -*-
"""
同步发票付款状态脚本 - 独立版本（不依赖Flask）

直接连接MySQL数据库执行更新，无需Flask环境。

使用方法:
    python scripts/20260110_sync_invoice_payment_status_standalone.py           # 预览模式
    python scripts/20260110_sync_invoice_payment_status_standalone.py --execute  # 执行模式
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


def get_ref_total_received(cursor, ref_id, header_id):
    """获取REF的实际已收款总额"""
    total_received = 0.0

    # 1. 直接关联的REF级别收款记录
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM project_receipts
        WHERE ref_id = %s AND status = 'confirmed'
    """, (ref_id,))
    result = cursor.fetchone()
    total_received += float(result[0]) if result and result[0] else 0

    # 2. 项目级别收款记录中分配给该REF的金额
    cursor.execute("""
        SELECT extra_info
        FROM project_receipts
        WHERE header_id = %s AND ref_id IS NULL AND status = 'confirmed' AND extra_info IS NOT NULL
    """, (header_id,))

    for row in cursor.fetchall():
        if row[0]:
            try:
                distribution_info = json.loads(row[0])
                if 'distribution' in distribution_info:
                    for dist in distribution_info['distribution']:
                        if dist.get('ref_id') == ref_id:
                            total_received += dist.get('amount', 0)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    return total_received


def get_invoice_received_from_refs(cursor, invoice_id, header_id, ref_ids_json):
    """根据发票关联的REF计算已收款金额"""
    if not ref_ids_json:
        return 0

    try:
        ref_id_list = json.loads(ref_ids_json)
    except (json.JSONDecodeError, TypeError):
        return 0

    if not ref_id_list:
        return 0

    total_received = 0
    for ref_id in ref_id_list:
        # 确保 ref_id 是整数类型
        ref_id_int = int(ref_id) if ref_id else None
        if ref_id_int:
            ref_received = get_ref_total_received(cursor, ref_id_int, header_id)
            total_received += ref_received

    return total_received


def get_invoice_direct_receipts(cursor, invoice_id):
    """获取直接关联到发票的收款总额"""
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM project_receipts
        WHERE invoice_id = %s AND status = 'confirmed'
    """, (invoice_id,))
    result = cursor.fetchone()
    return float(result[0]) if result and result[0] else 0


def get_invoice_allocated_receipts(cursor, invoice_id):
    """获取通过分配表关联到发票的收款总额"""
    cursor.execute("""
        SELECT COALESCE(SUM(ria.allocated_amount), 0) as total
        FROM receipt_invoice_allocations ria
        JOIN project_receipts pr ON ria.receipt_id = pr.id
        WHERE ria.invoice_id = %s AND pr.status = 'confirmed'
    """, (invoice_id,))
    result = cursor.fetchone()
    return float(result[0]) if result and result[0] else 0


def calculate_invoice_paid_amount(cursor, invoice):
    """计算发票的实际已付金额"""
    invoice_id = invoice['id']
    header_id = invoice['header_id']
    ref_ids = invoice['ref_ids']

    direct_amount = get_invoice_direct_receipts(cursor, invoice_id)
    allocated_amount = get_invoice_allocated_receipts(cursor, invoice_id)
    ref_amount = get_invoice_received_from_refs(cursor, invoice_id, header_id, ref_ids)

    if direct_amount > 0 or allocated_amount > 0:
        return max(direct_amount, allocated_amount)
    else:
        return ref_amount


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


def sync_invoice_payment_status(execute=False):
    """同步所有发票的付款状态"""
    print("=" * 80)
    print("发票付款状态同步脚本 (独立版本)")
    print("=" * 80)
    print(f"模式: {'执行模式' if execute else '预览模式（不修改数据）'}")
    print()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 获取所有未取消的发票
        cursor.execute("""
            SELECT id, invoice_number, header_id, amount, paid_amount, payment_status, ref_ids
            FROM project_invoices
            WHERE status != 'cancelled'
            ORDER BY id
        """)

        invoices = []
        for row in cursor.fetchall():
            invoices.append({
                'id': row[0],
                'invoice_number': row[1],
                'header_id': row[2],
                'amount': float(row[3]) if row[3] else 0,
                'paid_amount': float(row[4]) if row[4] else 0,
                'payment_status': row[5],
                'ref_ids': row[6]
            })

        print(f"共找到 {len(invoices)} 张有效发票")
        print()

        need_update = []
        for invoice in invoices:
            calculated_paid = calculate_invoice_paid_amount(cursor, invoice)
            calculated_status = determine_payment_status(invoice['amount'], calculated_paid)

            current_paid = invoice['paid_amount']
            current_status = invoice['payment_status']

            need_paid_update = abs(calculated_paid - current_paid) > 0.01
            need_status_update = calculated_status != current_status

            if need_paid_update or need_status_update:
                need_update.append({
                    'id': invoice['id'],
                    'invoice_number': invoice['invoice_number'],
                    'header_id': invoice['header_id'],
                    'amount': invoice['amount'],
                    'current_paid': current_paid,
                    'calculated_paid': calculated_paid,
                    'current_status': current_status,
                    'calculated_status': calculated_status
                })

        # 显示需要更新的发票
        if need_update:
            print(f"需要更新的发票: {len(need_update)} 张")
            print("-" * 100)
            print(f"{'发票号':<20} {'项目ID':<8} {'发票金额':>12} {'当前已付':>12} {'计算已付':>12} {'当前状态':<15} {'计算状态':<15}")
            print("-" * 100)

            for item in need_update:
                print(f"{item['invoice_number']:<20} {item['header_id']:<8} {item['amount']:>12.2f} "
                      f"{item['current_paid']:>12.2f} {item['calculated_paid']:>12.2f} "
                      f"{item['current_status']:<15} {item['calculated_status']:<15}")

            print("-" * 100)
            print()

            if execute:
                print("正在执行更新...")
                updated_count = 0
                for item in need_update:
                    cursor.execute("""
                        UPDATE project_invoices
                        SET paid_amount = %s, payment_status = %s
                        WHERE id = %s
                    """, (item['calculated_paid'], item['calculated_status'], item['id']))
                    updated_count += 1

                conn.commit()
                print(f"成功更新 {updated_count} 张发票")
            else:
                print("预览模式，未执行更新。")
                print("如需执行更新，请运行: py scripts/20260110_sync_invoice_payment_status_standalone.py --execute")
        else:
            print("所有发票的付款状态已是最新，无需更新。")

        print()
        print("=" * 80)

        # 统计信息
        print("\n统计信息:")
        print("-" * 50)

        cursor.execute("""
            SELECT payment_status, COUNT(*) as cnt,
                   COALESCE(SUM(amount), 0) as total_amount,
                   COALESCE(SUM(paid_amount), 0) as total_paid
            FROM project_invoices
            WHERE status != 'cancelled'
            GROUP BY payment_status
        """)

        total_invoices = 0
        total_amount = 0
        total_paid = 0

        for row in cursor.fetchall():
            status, count, amount, paid = row
            print(f"  {status:<15}: {count:>5} 张, 金额: {float(amount):>12.2f}, 已付: {float(paid):>12.2f}")
            total_invoices += count
            total_amount += float(amount)
            total_paid += float(paid)

        print("-" * 50)
        print(f"  {'合计':<15}: {total_invoices:>5} 张, 金额: {total_amount:>12.2f}, 已付: {total_paid:>12.2f}")
        print(f"  未收款总额: {total_amount - total_paid:>12.2f}")
        print()

        return len(need_update)

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
    result = sync_invoice_payment_status(execute=execute)
    return 0 if result >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
