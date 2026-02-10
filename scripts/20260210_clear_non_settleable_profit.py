# -*- coding: utf-8 -*-
"""
清除不可结算项目的利润分配

问题：之前利润分配没有检查可结算状态，导致不可结算的项目也分配了利润
本脚本：找出所有不可结算但已分配利润的项目，清零利润分配字段

运行方式: python scripts/20260210_clear_non_settleable_profit.py
预览模式: python scripts/20260210_clear_non_settleable_profit.py --dry-run
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def get_can_settle_ids():
    """获取所有可结算项目ID（ref>0, ref==eo, eo==paid, ref==invoiced, balance==0）"""
    rows = db.session.execute(text("""
        SELECT rc.header_id
        FROM (
            SELECT header_id, COUNT(*) AS ref_count
            FROM project_refs
            GROUP BY header_id
        ) rc
        LEFT JOIN (
            SELECT pr.header_id, COUNT(DISTINCT ii.ref_id) AS inv_count
            FROM project_refs pr
            JOIN invoice_items ii ON ii.ref_id = pr.id
            GROUP BY pr.header_id
        ) ic ON rc.header_id = ic.header_id
        LEFT JOIN (
            SELECT pr.header_id, COUNT(*) AS eo_count
            FROM project_eos pe
            JOIN project_refs pr ON pe.ref_id = pr.id
            GROUP BY pr.header_id
        ) ec ON rc.header_id = ec.header_id
        LEFT JOIN (
            SELECT pr.header_id, COUNT(*) AS paid_count
            FROM project_eos pe
            JOIN project_refs pr ON pe.ref_id = pr.id
            WHERE pe.is_paid = 1
            GROUP BY pr.header_id
        ) pc ON rc.header_id = pc.header_id
        LEFT JOIN (
            SELECT header_id, COALESCE(SUM(selling_price), 0) AS total_sell
            FROM project_refs
            GROUP BY header_id
        ) sc ON rc.header_id = sc.header_id
        LEFT JOIN (
            SELECT header_id, COALESCE(SUM(amount), 0) AS total_rcpt
            FROM project_receipts
            WHERE status = 'confirmed'
            GROUP BY header_id
        ) rcp ON rc.header_id = rcp.header_id
        WHERE rc.ref_count > 0
          AND rc.ref_count = COALESCE(ec.eo_count, 0)
          AND COALESCE(ec.eo_count, 0) = COALESCE(pc.paid_count, 0)
          AND rc.ref_count = COALESCE(ic.inv_count, 0)
          AND ABS(COALESCE(sc.total_sell, 0) - COALESCE(rcp.total_rcpt, 0)) < 0.01
    """)).fetchall()
    return {r[0] for r in rows}


def clear_non_settleable_profit(dry_run=False):
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("清除不可结算项目的利润分配")
        if dry_run:
            print("【预览模式】不会修改数据库")
        print("=" * 60)

        # 第1步：获取可结算项目ID
        print("\n--- 第1步：计算可结算项目 ---")
        can_settle_ids = get_can_settle_ids()
        print(f"  可结算项目: {len(can_settle_ids)} 个")

        # 第2步：找出不可结算但已分配利润的项目
        print("\n--- 第2步：查找需要清除的项目 ---")
        rows = db.session.execute(text(
            "SELECT id, hid, operator_profit, sales_profit, company_profit, order_type, is_settled "
            "FROM project_headers "
            "WHERE (operator_profit IS NOT NULL AND operator_profit != 0) "
            "   OR (sales_profit IS NOT NULL AND sales_profit != 0) "
            "   OR (company_profit IS NOT NULL AND company_profit != 0) "
            "   OR order_type IS NOT NULL"
        )).fetchall()

        to_clear = []
        for r in rows:
            pid, hid, op, sp, cp, ot, is_settled = r
            if pid not in can_settle_ids and not is_settled:
                to_clear.append({
                    'id': pid, 'hid': hid,
                    'operator_profit': float(op or 0),
                    'sales_profit': float(sp or 0),
                    'company_profit': float(cp or 0),
                    'order_type': ot
                })

        print(f"  已分配利润的项目: {len(rows)} 个")
        print(f"  其中不可结算（需清除）: {len(to_clear)} 个")
        print(f"  可结算（保留）: {len(rows) - len(to_clear)} 个")

        if not to_clear:
            print("\n没有需要清除的项目。")
            return

        # 第3步：显示详情并清除
        print(f"\n--- 第3步：清除利润分配 ---")
        for item in to_clear:
            print(f"  {item['hid']}: 员工={item['operator_profit']:.2f}, "
                  f"销售={item['sales_profit']:.2f}, "
                  f"公司={item['company_profit']:.2f}, "
                  f"类型={item['order_type']}")

        if not dry_run:
            ids_to_clear = [item['id'] for item in to_clear]
            # 分批更新（避免 SQL 过长）
            batch_size = 100
            for i in range(0, len(ids_to_clear), batch_size):
                batch = ids_to_clear[i:i + batch_size]
                placeholders = ','.join([':id' + str(j) for j in range(len(batch))])
                params = {'id' + str(j): batch[j] for j in range(len(batch))}
                db.session.execute(text(
                    f"UPDATE project_headers "
                    f"SET operator_profit = NULL, sales_profit = NULL, "
                    f"    company_profit = NULL, order_type = NULL "
                    f"WHERE id IN ({placeholders})"
                ), params)
            db.session.commit()

        print(f"\n--- 结果 ---")
        print(f"  清除了 {len(to_clear)} 个不可结算项目的利润分配")
        print("\n" + ("【预览完成，未修改数据库】" if dry_run else "清除完成！"))


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    clear_non_settleable_profit(dry_run=dry_run)
