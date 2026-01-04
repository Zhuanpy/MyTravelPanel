# -*- coding: utf-8 -*-
"""
更新发票状态脚本
根据付款金额自动更新发票状态：
- paid_amount >= amount: paid（已付款）
- paid_amount > 0: partial_paid（部分付款）
- paid_amount = 0: sent（未付款）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from App_new.exts import db
from App_new.config import Config


def create_minimal_app():
    """创建最小化应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def update_invoice_status():
    """更新所有发票状态"""
    app = create_minimal_app()

    with app.app_context():
        # 直接使用 SQL 查询
        result = db.session.execute(db.text("SELECT id, invoice_number, amount, paid_amount, status FROM project_invoices"))
        invoices = result.fetchall()

        updated_count = 0
        status_summary = {
            'paid': 0,
            'partial_paid': 0,
            'sent': 0,
            'unchanged': 0
        }

        print(f"开始处理 {len(invoices)} 张发票...")
        print("-" * 50)

        for invoice in invoices:
            inv_id = invoice[0]
            invoice_number = invoice[1]
            amount = float(invoice[2] or 0)
            paid_amount = float(invoice[3] or 0)
            old_status = invoice[4]

            # 跳过已取消的发票
            if old_status == 'cancelled':
                continue

            # 根据付款金额判断状态
            if amount > 0 and paid_amount >= amount:
                new_status = 'paid'
            elif paid_amount > 0:
                new_status = 'partial_paid'
            else:
                new_status = 'sent'  # 未付款

            # 如果状态有变化，更新
            if old_status != new_status:
                print(f"发票 {invoice_number}: {old_status} -> {new_status} "
                      f"(金额: {amount}, 已付: {paid_amount})")
                db.session.execute(
                    db.text("UPDATE project_invoices SET status = :status WHERE id = :id"),
                    {'status': new_status, 'id': inv_id}
                )
                updated_count += 1
                status_summary[new_status] = status_summary.get(new_status, 0) + 1
            else:
                status_summary['unchanged'] += 1

        # 提交更改
        if updated_count > 0:
            try:
                db.session.commit()
                print("-" * 50)
                print(f"成功更新 {updated_count} 张发票状态")
            except Exception as e:
                db.session.rollback()
                print(f"更新失败: {e}")
                return
        else:
            print("没有需要更新的发票")

        # 打印统计
        print("-" * 50)
        print("状态统计:")
        print(f"  - Paid (已付款): {status_summary.get('paid', 0)}")
        print(f"  - Partial Paid (部分付款): {status_summary.get('partial_paid', 0)}")
        print(f"  - Unpaid (未付款): {status_summary.get('sent', 0)}")
        print(f"  - 未变更: {status_summary.get('unchanged', 0)}")


if __name__ == '__main__':
    update_invoice_status()
