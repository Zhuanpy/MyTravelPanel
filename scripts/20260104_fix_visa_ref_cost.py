# -*- coding: utf-8 -*-
"""
修复 Visa REF 的 cost 数据
问题：extra_info 中的 adult_cost/child_cost/infant_cost 为 0 或缺失，
      但 REF 本身的 cost_price 有值

修复逻辑：
1. 查找所有签证类型的 REF
2. 如果 cost_price > 0 但 extra_info 中的 cost 字段为 0 或缺失
3. 根据 adult_qty 将 cost_price 分配到 adult_cost
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from App_new.exts import db
from App_new.config import Config
from sqlalchemy import text


def create_minimal_app():
    """创建最小化应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def fix_visa_ref_cost():
    """修复 Visa REF 的 cost 数据"""

    # 获取签证业务类型 ID
    result = db.session.execute(text("SELECT id FROM business_types WHERE code = 'visa' OR name = '签证' LIMIT 1"))
    row = result.fetchone()
    if not row:
        print("未找到签证业务类型")
        return

    visa_type_id = row[0]
    print(f"签证业务类型 ID: {visa_type_id}")

    # 查找所有签证类型的 REF
    result = db.session.execute(text("""
        SELECT id, ref_number, cost_price, selling_price, extra_info
        FROM project_refs
        WHERE ref_type_id = :visa_type_id AND extra_info IS NOT NULL
    """), {"visa_type_id": visa_type_id})

    visa_refs = result.fetchall()
    print(f"找到 {len(visa_refs)} 个签证 REF")

    fixed_count = 0

    for ref in visa_refs:
        ref_id, ref_number, cost_price, selling_price, extra_info_str = ref

        try:
            extra_info = json.loads(extra_info_str)
        except json.JSONDecodeError:
            continue

        # 检查是否需要修复
        cost_price = float(cost_price) if cost_price else 0
        adult_cost = float(extra_info.get('adult_cost', 0) or 0)
        child_cost = float(extra_info.get('child_cost', 0) or 0)
        infant_cost = float(extra_info.get('infant_cost', 0) or 0)
        total_extra_cost = adult_cost + child_cost + infant_cost

        # 如果 REF 的 cost_price > 0 但 extra_info 中的 cost 总和为 0
        if cost_price > 0 and total_extra_cost == 0:
            adult_qty = int(extra_info.get('adult_qty', 1) or 1)
            child_qty = int(extra_info.get('child_qty', 0) or 0)
            infant_qty = int(extra_info.get('infant_qty', 0) or 0)
            total_qty = adult_qty + child_qty + infant_qty

            if total_qty > 0:
                # 按人数比例分配 cost
                unit_cost = cost_price / total_qty
                extra_info['adult_cost'] = round(unit_cost, 2) if adult_qty > 0 else 0
                extra_info['child_cost'] = round(unit_cost, 2) if child_qty > 0 else 0
                extra_info['infant_cost'] = round(unit_cost, 2) if infant_qty > 0 else 0
            else:
                # 如果没有人数，全部分配给 adult
                extra_info['adult_cost'] = cost_price
                extra_info['child_cost'] = 0
                extra_info['infant_cost'] = 0

            new_extra_info = json.dumps(extra_info, ensure_ascii=False)
            db.session.execute(text("""
                UPDATE project_refs SET extra_info = :extra_info WHERE id = :ref_id
            """), {"extra_info": new_extra_info, "ref_id": ref_id})

            fixed_count += 1
            print(f"  修复 REF {ref_id} ({ref_number}): cost_price={cost_price}, "
                  f"adult_cost={extra_info['adult_cost']}, "
                  f"child_cost={extra_info['child_cost']}, "
                  f"infant_cost={extra_info['infant_cost']}")

    if fixed_count > 0:
        db.session.commit()
        print(f"\n成功修复 {fixed_count} 个 REF")
    else:
        print("\n没有需要修复的 REF")


def show_ref_status(ref_id):
    """显示指定 REF 的状态"""
    result = db.session.execute(text("""
        SELECT r.id, r.ref_number, r.cost_price, r.selling_price, r.extra_info,
               e.status as eo_status, e.pay_amount as eo_pay_amount
        FROM project_refs r
        LEFT JOIN project_eos e ON e.ref_id = r.id
        WHERE r.id = :ref_id
    """), {"ref_id": ref_id})

    row = result.fetchone()
    if row:
        ref_id, ref_number, cost_price, selling_price, extra_info_str, eo_status, eo_pay_amount = row
        print(f"=== REF {ref_id} ({ref_number}) 状态 ===")
        print(f"  cost_price: {cost_price}")
        print(f"  selling_price: {selling_price}")
        if extra_info_str:
            try:
                extra = json.loads(extra_info_str)
                print(f"  extra_info.adult_qty: {extra.get('adult_qty', 'N/A')}")
                print(f"  extra_info.adult_selling: {extra.get('adult_selling', 'N/A')}")
                print(f"  extra_info.adult_cost: {extra.get('adult_cost', 'N/A')}")
            except:
                pass
        print(f"  EO status: {eo_status}")
        print(f"  EO pay_amount: {eo_pay_amount}")
        print()
    else:
        print(f"REF {ref_id} not found")


def main():
    app = create_minimal_app()
    with app.app_context():
        # 先查看 REF 447 的情况
        show_ref_status(447)

        # 执行修复
        fix_visa_ref_cost()

        # 再次查看 REF 447 的情况
        print("\n=== 修复后 ===")
        show_ref_status(447)


if __name__ == '__main__':
    main()
