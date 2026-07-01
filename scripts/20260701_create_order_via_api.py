# -*- coding: utf-8 -*-
"""
纯 API 创建机票订单参考脚本（无需浏览器/Selenium）

用已登录的 session cookie 直接串联后端已有 JSON 接口，完成整条下单流程：
    1. 复制项目            POST /projects/detail/<id>/copy
    2. 管理乘客            DELETE/POST /projects/<hid>/members[...] + set-leader
    3. 一键创建机票REF     POST /projects/ref/flight/quick-create/<hid>   ← 本次新增
    4. 生成EO             POST /projects/eo/quick_create/<ref_id>
    5. 生成发票            POST /projects/invoice/header/<hid>/quick-create

所有接口均返回 JSON，全程无需页面跳转/DOM 操作。

运行：python scripts/20260701_create_order_via_api.py
（先按需修改 BASE_URL / 登录信息 / ORDER 数据）
"""

import requests

# ============ 配置 ============
BASE_URL = "https://joyesc.com"          # 线上域名，本地改成 http://127.0.0.1:5000
LOGIN_URL = f"{BASE_URL}/auth/login"     # 登录端点（按实际路由调整）
USERNAME = "your_username"
PASSWORD = "your_password"

# 源项目（用于复制继承客户公司/联系人）
SOURCE_PROJECT_ID = 3200

# 本次订单数据
ORDER = {
    "supplier_id": 256,                  # ZHANG ZHUAN OCBC MASTER
    "remarks": "ZHOU YONGFA 机票订单",
    "leader_name": "ZHOU YONGFA",
    "passengers": [
        {
            "name": "ZHOU YONGFA",
            "type": "adult",
            "selling_price": 255,
            "cost_price": 224.20,
            # "passport_number": "E12345678",
        },
    ],
    "segments": [
        {
            "flight_number": "HU448", "cabin_code": "Y",
            "departure_airport": "SIN", "arrival_airport": "HAK",
            "departure_date": "2026-07-03", "departure_time": "04:40",
            "arrival_date": "2026-07-03", "arrival_time": "08:25",
        },
        {
            "flight_number": "HU6257", "cabin_code": "Y",
            "departure_airport": "HAK", "arrival_airport": "KHN",
            "departure_date": "2026-07-03", "departure_time": "10:30",
            "arrival_date": "2026-07-03", "arrival_time": "12:50",
        },
    ],
}
# ============================


def login(session):
    """表单登录，session 内保留 cookie。字段名按实际登录表单调整。"""
    resp = session.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD},
        allow_redirects=True,
    )
    resp.raise_for_status()
    print(f"[登录] {resp.status_code} {resp.url}")


def copy_project(session, source_id):
    """复制项目，返回 (new_project_id, new_hid)。header_id 即项目主表 id。"""
    resp = session.post(f"{BASE_URL}/projects/detail/{source_id}/copy")
    resp.raise_for_status()
    data = resp.json()
    new_id = data.get("new_project_id") or data.get("new_hid")
    print(f"[复制项目] source={source_id} -> new={new_id}")
    return new_id


def reset_members(session, hid, passengers):
    """清空原乘客并按 ORDER 重建，首位设为 Leader。返回 leader 的 member_id。"""
    # 拉现有乘客
    cur = session.get(f"{BASE_URL}/projects/{hid}/members").json()
    for m in cur.get("members", cur if isinstance(cur, list) else []):
        mid = m.get("id")
        if mid:
            session.delete(f"{BASE_URL}/projects/{hid}/members/{mid}")
    print(f"[乘客] 已清空原有乘客")

    leader_member_id = None
    for i, p in enumerate(passengers):
        body = {
            "member_name": p["name"],
            "member_name_en": p.get("name"),
            # 可选：title/gender/date_of_birth/nationality/id_type/id_number/
            #       passport_issuing_country/passport_expiry_date 等
        }
        r = session.post(f"{BASE_URL}/projects/{hid}/members", json=body).json()
        mid = r.get("member_id") or (r.get("member") or {}).get("id")
        print(f"[乘客] 添加 {p['name']} -> member_id={mid}")
        if i == 0:
            leader_member_id = mid

    # 显式设 Leader（注意正确 URL：/members/<member_id>/set-leader）
    if leader_member_id:
        session.post(f"{BASE_URL}/projects/{hid}/members/{leader_member_id}/set-leader")
        print(f"[乘客] 设 Leader member_id={leader_member_id}")
    return leader_member_id


def quick_create_ref(session, hid, order):
    """一键创建机票REF，返回 ref。"""
    body = {
        "supplier_id": order["supplier_id"],
        "remarks": order.get("remarks"),
        "leader_name": order.get("leader_name"),
        "passengers": order["passengers"],
        "segments": order["segments"],
    }
    resp = session.post(f"{BASE_URL}/projects/ref/flight/quick-create/{hid}", json=body)
    resp.raise_for_status()
    ref = resp.json()
    if not ref.get("success"):
        raise RuntimeError(f"创建REF失败：{ref.get('error')}")
    print(f"[REF] ref_id={ref['ref_id']} {ref['ref_number']} {ref['description']}")
    return ref


def quick_create_eo(session, ref_id):
    resp = session.post(f"{BASE_URL}/projects/eo/quick_create/{ref_id}")
    resp.raise_for_status()
    eo = resp.json()
    print(f"[EO] {eo.get('eo_number')} (id={eo.get('eo_id')})")
    return eo


def quick_create_invoice(session, hid, ref):
    """发票 quick-create 需要 refs[].ref_id 及金额。total 取 REF 售价。"""
    body = {
        "refs": [{
            "ref_id": ref["ref_id"],
            "total": ref.get("selling_price") or 0,
            "gross": ref.get("selling_price") or 0,
            "discount": 0,
            "tax": 0,
            "show_on_invoice": True,
        }],
    }
    resp = session.post(f"{BASE_URL}/projects/invoice/header/{hid}/quick-create", json=body)
    resp.raise_for_status()
    inv = resp.json()
    print(f"[发票] {inv.get('invoice_number')} (id={inv.get('invoice_id')})")
    return inv


def main():
    s = requests.Session()
    login(s)

    hid = copy_project(s, SOURCE_PROJECT_ID)
    reset_members(s, hid, ORDER["passengers"])
    ref = quick_create_ref(s, hid, ORDER)
    quick_create_eo(s, ref["ref_id"])
    quick_create_invoice(s, hid, ref)

    print(f"\n✅ 完成。项目ID={hid}")


if __name__ == "__main__":
    main()
