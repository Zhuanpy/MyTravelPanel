# -*- coding: utf-8 -*-
"""
修复 Invoice 与 REF 的关联

问题：Athina 导入时只将 ref_ids 存为 JSON，没有创建 InvoiceItem 记录
解决：根据 ProjectInvoice.ref_ids 创建 InvoiceItem 记录

运行方式: python scripts/fix_invoice_ref_link.py
"""

import sys
import os
import json
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem


def fix_invoice_ref_links():
    """修复 Invoice 与 REF 的关联"""
    app = create_app()

    with app.app_context():
        # 获取所有有 ref_ids 但没有 InvoiceItem 的发票
        invoices = ProjectInvoice.query.all()

        total = len(invoices)
        fixed_count = 0
        skipped_count = 0
        error_count = 0
        already_linked = 0

        print(f"开始检查 {total} 张发票...")
        print("=" * 70)

        for invoice in invoices:
            try:
                # 检查是否已有 InvoiceItem
                existing_items = InvoiceItem.query.filter_by(invoice_id=invoice.id).count()
                if existing_items > 0:
                    already_linked += 1
                    continue

                # 解析 ref_ids
                ref_ids = []
                if invoice.ref_ids:
                    try:
                        ref_ids = json.loads(invoice.ref_ids)
                    except json.JSONDecodeError:
                        # 可能是逗号分隔的字符串
                        ref_ids = [int(x.strip()) for x in invoice.ref_ids.split(',') if x.strip().isdigit()]

                if not ref_ids:
                    # 尝试通过 header_id 找到对应的 REF
                    if invoice.header_id:
                        refs = ProjectRef.query.filter_by(header_id=invoice.header_id).all()
                        ref_ids = [ref.id for ref in refs]

                if not ref_ids:
                    skipped_count += 1
                    print(f"  跳过 Invoice {invoice.invoice_number}: 无法找到关联的 REF")
                    continue

                # 解析 invoice_items JSON 获取明细信息
                items_data = []
                if invoice.invoice_items:
                    try:
                        items_data = json.loads(invoice.invoice_items)
                    except json.JSONDecodeError:
                        pass

                # 为每个 REF 创建 InvoiceItem
                created_items = 0
                for i, ref_id in enumerate(ref_ids):
                    ref = ProjectRef.query.get(ref_id)
                    if not ref:
                        print(f"    警告: REF ID {ref_id} 不存在，跳过")
                        continue

                    # 获取对应的 item 数据（如果有）
                    item_data = items_data[i] if i < len(items_data) else {}

                    # 创建 InvoiceItem
                    invoice_item = InvoiceItem(
                        invoice_id=invoice.id,
                        ref_id=ref_id,
                        description=item_data.get('itin_desc') or ref.description or f"REF {ref.ref_number}",
                        quantity=1,
                        unit_price=Decimal(str(ref.selling_price or 0)),
                        total_price=Decimal(str(ref.selling_price or 0)),
                        remarks=f"从 Athina 导入修复创建"
                    )
                    db.session.add(invoice_item)
                    created_items += 1

                if created_items > 0:
                    fixed_count += 1
                    print(f"  修复 Invoice {invoice.invoice_number}: 创建 {created_items} 个 InvoiceItem")

            except Exception as e:
                error_count += 1
                print(f"  错误 Invoice {invoice.invoice_number}: {str(e)}")

        # 提交更改
        try:
            db.session.commit()
            print("\n数据已保存")
        except Exception as e:
            db.session.rollback()
            print(f"\n保存失败: {str(e)}")
            return

        # 输出统计
        print("\n" + "=" * 70)
        print(f"统计:")
        print(f"  总发票数: {total}")
        print(f"  已有关联: {already_linked}")
        print(f"  成功修复: {fixed_count}")
        print(f"  跳过: {skipped_count}")
        print(f"  错误: {error_count}")


if __name__ == '__main__':
    fix_invoice_ref_links()
