# -*- coding: utf-8 -*-
"""
修复手机端历史订单：将 notes 字段中的 JSON 数据迁移到 OrderItem.properties。

背景: App_new/mobile/routes.py 之前的实现错误地把 product_id / variant_id / visit_date
等结构化字段通过 json.dumps() 写入了 order.notes，导致订单详情页"备注"区域显示一串 JSON。
桌面端的正确做法是放入 OrderItem.properties（JSON 列），notes 只用于人类可读的留言。

本脚本会:
1. 找出 notes 以 "{" 开头的订单（疑似 JSON）
2. 解析 JSON
3. 如果订单还没有 OrderItem，则根据 JSON 和订单的金额/数量新建一条 OrderItem
4. 如果已有 OrderItem 但没有 properties，则把 JSON 回填到 properties
5. 清空 notes 字段

运行方式: python scripts/20260417_fix_mobile_order_notes.py
         python scripts/20260417_fix_mobile_order_notes.py --dry-run   # 只预览，不改库
"""

import sys
import os
import json
import argparse
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.member.models.order import Order, OrderItem


def _looks_like_json(s):
    if not s:
        return False
    s = s.strip()
    return s.startswith('{') and s.endswith('}')


def _build_item_name(order, props):
    variant_name = props.get('variant_name') or ''
    if order.service_type == 'ticket' and variant_name:
        return f"{order.service_name} - {variant_name}"
    return order.service_name


def _derive_quantity(props):
    qty = 0
    for key in ('adult_count', 'child_count', 'infant_count'):
        val = props.get(key)
        if val is None:
            continue
        try:
            qty += int(val)
        except (TypeError, ValueError):
            pass
    return qty or 1


def _derive_unit_price(props):
    val = props.get('adult_price')
    if val is None:
        return Decimal('0')
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal('0')


def migrate(dry_run=False):
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("修复手机端订单 notes 字段（JSON → OrderItem.properties）")
        print(f"模式: {'DRY RUN（只预览）' if dry_run else '实际写入'}")
        print("=" * 60)

        orders = Order.query.filter(Order.notes.isnot(None)).all()
        json_orders = [o for o in orders if _looks_like_json(o.notes)]
        print(f"共扫描 {len(orders)} 个有 notes 的订单，其中 {len(json_orders)} 个疑似 JSON")

        fixed_new_item = 0
        fixed_backfill = 0
        skipped_bad_json = 0
        cleared_only = 0

        for order in json_orders:
            try:
                props = json.loads(order.notes)
                if not isinstance(props, dict):
                    raise ValueError('not a JSON object')
            except Exception as e:
                print(f"  [跳过] 订单#{order.id} {order.order_number} JSON 解析失败: {e}")
                skipped_bad_json += 1
                continue

            existing_items = order.order_items
            if not existing_items:
                # 根据 notes 中的数据新建 OrderItem
                item = OrderItem(
                    order_id=order.id,
                    item_name=_build_item_name(order, props),
                    item_description='',
                    item_type=order.service_type,
                    quantity=_derive_quantity(props),
                    unit_price=_derive_unit_price(props),
                    total_price=order.total_amount or Decimal('0'),
                    properties=props,
                )
                if not dry_run:
                    db.session.add(item)
                print(f"  [新建] 订单#{order.id} {order.order_number} → 新建 OrderItem，props 保留 {len(props)} 个字段")
                fixed_new_item += 1
            else:
                # 有 item 但可能没 properties，回填
                target = existing_items[0]
                if not target.properties:
                    target.properties = props
                    if not dry_run:
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(target, 'properties')
                    print(f"  [回填] 订单#{order.id} {order.order_number} → OrderItem#{target.id} 回填 properties")
                    fixed_backfill += 1
                else:
                    print(f"  [清空] 订单#{order.id} {order.order_number} → OrderItem 已有 properties，仅清空 notes")
                    cleared_only += 1

            # 清空 notes
            if not dry_run:
                order.notes = None

        if not dry_run:
            db.session.commit()

        print("-" * 60)
        print(f"新建 OrderItem: {fixed_new_item}")
        print(f"回填 properties: {fixed_backfill}")
        print(f"仅清空 notes:    {cleared_only}")
        print(f"JSON 解析失败:   {skipped_bad_json}")
        print(f"{'（dry-run 未提交）' if dry_run else '已提交'}")
        print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='只预览不写入数据库')
    # server_update.sh 统一传 --execute，这里接受但等同于默认行为
    parser.add_argument('--execute', action='store_true', help='兼容部署脚本，默认即为执行')
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
