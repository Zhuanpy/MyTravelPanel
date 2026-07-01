# -*- coding: utf-8 -*-
"""
纯 API 创建机票订单参考脚本（token 版，无需浏览器/Selenium/session 登录）

用 API Token（X-API-Key）无状态串联后端 JSON 接口，一条流水线建单：
    1. 复制项目            POST /projects/detail/<id>/copy
                           → new_project_id / new_hid / new_ref_ids(复制来的旧REF)
    2. 重建人员名单        GET  /projects/<pid>/members        (读旧成员)
                           DELETE /projects/<pid>/members/<mid> (逐个删)
                           POST /projects/<pid>/members/batch   (批量加新，首个自动Leader)
    3. 删复制来的旧REF     POST /projects/ref/delete/<ref_id>?format=json
    4. 一键建机票REF+EO+发票 POST /projects/ref/flight/quick-create/<pid>
                           body 带 auto_eo / auto_invoice

设计要点（本次调试固化的经验）：
    - 全程用 X-API-Key，不走 session 登录 → 不掉线、不翻页。
    - 只用 JSON 接口，绝不正则爬 detail 页面 HTML（新复制项目的 HTML 结构会变）。
    - 复制来的旧 REF 一律删掉重建，不去"原地编辑"它的乘客/价格（那是两张独立表，
      改项目成员不会改 REF 乘客；乘客更新接口也不允许改 name）。

生成 token：
    python scripts/20260622_manage_api_token.py create <你的邮箱> api-agent
运行：
    python scripts/20260701_create_order_via_api.py
"""

import requests

# ============ 配置 ============
BASE_URL = "https://joyesc.com"          # 本地测试改 http://127.0.0.1:5000
API_TOKEN = "mtp_你的token"               # 由 20260622_manage_api_token.py 生成

SOURCE_PROJECT_ID = 3200                 # 源项目（用于复制继承客户公司/联系人）

ORDER = {
    "supplier_id": 256,                  # 供应商 CustomerCompany.id
    "remarks": "ZHOU YONGFA 机票订单",
    # 乘客：同时用于「人员名单」和「机票REF乘客」（两张独立表，需分别写入）
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


def make_session(token):
    """创建带 API Token 的 Session；之后所有请求自动携带，无需登录。"""
    s = requests.Session()
    s.headers["X-API-Key"] = token
    return s


def _json(resp):
    """统一取 JSON 并在失败时抛出带上下文的错误。"""
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(f"{resp.request.method} {resp.url} 失败：{data.get('message') or data.get('error')}")
    return data


def copy_project(s, source_id):
    """复制项目。返回 (pid, hid, old_ref_ids)。old_ref_ids = 复制来的旧REF，待删。"""
    data = _json(s.post(f"{BASE_URL}/projects/detail/{source_id}/copy"))
    pid = data["new_project_id"]
    hid = data.get("new_hid")
    old_ref_ids = data.get("new_ref_ids", [])
    print(f"[复制] source={source_id} → 项目 {hid} (id={pid})，复制来的旧REF={old_ref_ids}")
    return pid, hid, old_ref_ids


def reset_members(s, pid, passengers):
    """清空人员名单并按乘客重建（GET→逐个DELETE→batch）。batch 首个自动设 Leader。"""
    # 读旧成员（JSON，不爬 HTML）
    cur = _json(s.get(f"{BASE_URL}/projects/{pid}/members"))
    for m in cur.get("data", []):
        s.delete(f"{BASE_URL}/projects/{pid}/members/{m['id']}")
    print(f"[人员] 清空旧成员 {len(cur.get('data', []))} 名")

    body = {"members": [
        {"member_name": p["name"], "member_name_en": p.get("name")}
        for p in passengers
    ]}
    added = _json(s.post(f"{BASE_URL}/projects/{pid}/members/batch", json=body))
    print(f"[人员] 批量添加 {len(added.get('data', []))} 名（首个已设 Leader）")


def delete_refs(s, ref_ids):
    """删除复制来的旧 REF（JSON 返回，需 ?format=json）。"""
    for rid in ref_ids:
        _json(s.post(f"{BASE_URL}/projects/ref/delete/{rid}?format=json"))
        print(f"[删REF] 已删旧REF id={rid}")


def quick_create_flight(s, pid, order):
    """一键建 机票REF + EO + 发票。返回结果字典。"""
    body = {
        "supplier_id": order["supplier_id"],
        "remarks": order.get("remarks"),
        "leader_name": order["passengers"][0]["name"],
        "passengers": order["passengers"],
        "segments": order["segments"],
        "auto_eo": True,
        "auto_invoice": True,
    }
    r = _json(s.post(f"{BASE_URL}/projects/ref/flight/quick-create/{pid}", json=body))
    print(f"[建单] REF {r['ref_number']}(id={r['ref_id']}) "
          f"EO {r.get('eo_number')} 发票 {r.get('invoice_number')}")
    if r.get("eo_error"):
        print(f"   ⚠️ EO: {r['eo_error']}")
    if r.get("invoice_error"):
        print(f"   ⚠️ 发票: {r['invoice_error']}")
    return r


def create_order(s, source_id, order):
    """完整下单流水线：复制 → 重建人员 → 删旧REF → 一键建REF+EO+发票。"""
    pid, hid, old_ref_ids = copy_project(s, source_id)
    reset_members(s, pid, order["passengers"])
    delete_refs(s, old_ref_ids)                 # 删掉复制来的旧REF，避免重复
    result = quick_create_flight(s, pid, order)
    result.update({"project_id": pid, "hid": hid})
    return result


def main():
    s = make_session(API_TOKEN)
    result = create_order(s, SOURCE_PROJECT_ID, ORDER)
    print(f"\n✅ 完成：项目 {result['hid']}(id={result['project_id']}) / "
          f"REF {result['ref_number']} / EO {result.get('eo_number')} / "
          f"发票 {result.get('invoice_number')}")

    # 批量下单示例：一个 token 连做 N 单，中间无任何页面切换
    # for od in [ORDER_A, ORDER_B, ...]:
    #     create_order(s, SOURCE_PROJECT_ID, od)


if __name__ == "__main__":
    main()
