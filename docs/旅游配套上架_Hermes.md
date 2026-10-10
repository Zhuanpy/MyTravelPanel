# 旅游配套上架（供 Hermes 调用）

把供应商给的配套资料（txt / Word / 网页复制的文字 + 图片）整理成产品，上传到产品库，
最终显示在公开页 `https://joyesc.com/public/tour-package/<product_id>`。

- **Base URL**: `https://joyesc.com`（本地调试 `http://127.0.0.1:5000`）
- **鉴权**: 请求头 `X-API-Key: <staff token>`，带 token 自动免 CSRF。401/403 先打 `GET /api/hermes/whoami` 自检，**不要改用账号密码登录浏览器**。
- **核心接口**: `POST /tour/products/api/upsert`，一个产品一次调用，整个请求一个事务。

---

## 1. 输入约定（给人看的：资料怎么放）

每个产品一个文件夹：

```
Packages/
  Batam Lobster 2D1N/
    package.txt        ← 正文（名称、Include、Exclude、Itinerary）
    cover.jpg          ← 封面（文件名含 cover）
    01.jpg 02.jpg ...  ← 其余图片进图库
```

`package.txt` 开头可以写一个**表头块**，写了就以表头为准，不用 Hermes 去猜：

```
Code: BTM-LOBSTER-2D1N
Supplier: PT. NUSAJAYA INDOFAST T&T
City: Batam
Country: Indonesia
Days: 2
Price: Twin 168 / Single 228 / Child No Bed 128 SGD
Valid: 2026-10-01 ~ 2027-03-31
---
（以下为正文）
```

---

## 2. 处理流程（Hermes 照做）

1. **读文件夹** → 读 `package.txt` 表头块和正文，列出图片。
2. **查重**：`GET /tour/products/lookup?code=<Code>`；没有 Code 时用 `?q=<名称关键词>`。
   - 命中同名/同编号产品 → 这是**更新**，upsert 时带上 `product_code`（或 `product_id`）。
   - 名称相似但不确定是不是同一个 → 停下来问人，不要新建重复产品。
3. **整理 JSON**（规则见 §3）→ `POST /tour/products/api/upsert`。
4. **传图片**（有的话）：
   - 封面：`POST /tour/products/<pid>/upload-image`，form `kind=cover`，`image=<文件>`
   - 图库：同一接口，`kind=gallery`，可以一次传多个 `image`
5. **验收**：`GET /tour/products/<pid>/json` 读回来，核对名称、天数、行程天数、价格。
6. **汇报给人**：产品 id、编号、编辑页链接（`edit_url`）、返回的 `warnings`、哪些字段是你推断的。
7. **不要自己上架**。新建产品默认 `draft`（公开页看不到）。人确认后再
   `POST /tour/products/<pid>/patch {"product_status": "active"}`。

---

## 3. txt → JSON 字段对照

| JSON 字段 | 来源 / 规则 |
|---|---|
| `product_code` | 表头 `Code`。没有就**不传**，服务器自动生成（如 `TOU-2610-001`），并把生成的编号报给人。批量时建议人定规则：`城市缩写-特色-天数`，例 `BTM-LOBSTER-2D1N` |
| `product_name` | 正文第一行标题（去掉 "ALL Packages" 这类页面杂字）。**英文** |
| `supplier_name` | 表头 `Supplier`；没有则用正文里出现的地接名（如 "PT. Nusajaya Indofast T&T"）。必须和系统里公司名**完全一致**，不确定先 `GET /api/hermes/companies/search?q=&role=supplier` 查。不存在只会出 warning、不报错 |
| `city_name` / `country_name` | 目的地城市（英文，如 `Batam` / `Indonesia`）。城市不存在会自动建 |
| `departure_city` / `destination_city` | 出发地 / 目的地（英文） |
| `duration_days` | 表头 `Days`，没有则数 Itinerary 里的 Day 数 |
| `product_type` | `跟团游` / `自由行` / `定制游` / `当地游` 之一（系统内部值，保持中文）。有导游 + 包车 → `跟团游` |
| `currency` | 默认 `SGD` |
| `base_price` / `child_price` | 公开页大字显示的"起价"。有价格方案时取 Twin（每人）作 `base_price`、Child No Bed 作 `child_price` |
| `price_variants` | 见 §4。**传了就整份替换**该产品原有价格方案 |
| `product_description` | 用 1–3 句英文概括（目的地、天数、亮点）。原文没有就自己写，不要留空——留空公开页会显示中文占位文字 |
| `included_services` | Include 段，**一行一项**（`\n` 分隔），保留原文 emoji，去掉行尾句号 |
| `excluded_services` | Exclude 段，规则同上 |
| `important_notes` | 原文中的注意事项（集合时间、行程可能变动、退房时间等），一行一项，英文 |
| `tags` | 数组，2–4 个英文短标签，如 `["Batam", "Seafood", "Short Trip"]` |
| `valid_from` / `valid_until` | `YYYY-MM-DD`。没有就不传；**已过期的日期公开页会 404** |
| `days` | 见 §5。**传了就整份替换**该产品原有行程 |

**语言**：面向客户的字段一律英文（名称、描述、Include/Exclude、行程）。原文是中文就翻译。

**不要编造**：价格、有效期、供应商这三项原文没有就不传，在汇报里列为"缺失"，让人补。

---

## 4. 价格方案 `price_variants`

```json
"price_variants": [
  {"variant_name": "Weekday", "twin_price": 168, "single_price": 228, "child_no_bed_price": 128,
   "cost_twin_price": 140, "start_date": "2026-10-01", "end_date": "2027-03-31", "is_primary": true},
  {"variant_name": "Weekend", "twin_price": 188, "single_price": 258}
]
```

- `variant_name` 必填。价格字段：`single_price` `twin_price` `third_pax_price` `child_no_bed_price`；
  成本：`cost_single_price` `cost_twin_price` `cost_third_pax_price` `cost_child_no_bed_price`
- 价格都是**每人**价。原文写 "per room" 要先除以人数，并在汇报里注明
- 都没标 `is_primary` 时，第一个自动设为主要价格
- 只想改价格不动其它：只传 `product_code` + `price_variants`

---

## 5. 逐日行程 `days`

```json
"days": [
  {"day_number": 1, "day_title": "Singapore – Batam City & Shopping Tour", "content": "…"},
  {"day_number": 2, "day_title": "Check-out – Return to Singapore", "content": "…"}
]
```

- 按原文 `Day 01` / `Day 02 or Next Day` 拆天；`day_title` 自己概括成"起点 – 主要内容"
- `content` 保留原文的分段和 `📌` 景点清单，用 `\n` 换行；删掉重复的营销句
- 自费项目保留 "(own expense)" 标注，不要删

---

## 6. 返回值与 warnings

```json
{"success": true, "action": "created", "product_id": 259, "product_code": "BTM-LOBSTER-2D1N",
 "product_status": "draft", "itinerary_count": 2, "price_variant_count": null,
 "warnings": ["没有封面图，用 /tour/products/<pid>/upload-image (kind=cover) 上传"],
 "edit_url": "/tour/products/259/edit", "public_url": "/public/tour-package/259"}
```

- `action`: `created` / `updated`；`itinerary_count` / `price_variant_count` 为 `null` 表示这次没传、原数据没动
- `warnings`（不阻断，但要转告人）：
  - 供应商不存在，未关联
  - 没有 `base_price` 也没有 `price_variants`，公开页不显示价格
  - 没有封面图
  - `valid_until` 已过期，公开页会 404
- 失败：`400`（缺 `product_name`、日期格式错等，`message` 说明原因）/ `404`（`product_id` 不存在）。整次请求回滚，可以修正后直接重发

**可以放心重发**：同一个 `product_code` 再调一次是更新，不会产生重复产品。

---

## 7. 完整示例（Python）

```python
import json, requests
BASE = "https://joyesc.com"
H = {"X-API-Key": HERMES_TOKEN}

payload = {
    "product_code": "BTM-LOBSTER-2D1N",
    "product_name": "Exclusive Batam Tour Package with a Complimentary Half Lobster",
    "supplier_name": "PT. NUSAJAYA INDOFAST T&T",
    "city_name": "Batam", "country_name": "Indonesia",
    "departure_city": "Singapore", "destination_city": "Batam",
    "product_type": "跟团游", "duration_days": 2, "currency": "SGD",
    "product_description": "A 2-day Batam getaway from Singapore with ...",
    "included_services": "⛴️ Round-trip Ferry Tickets (Singapore ⇄ Batam)\n🏨 Hotel Accommodation with Daily Breakfast",
    "excluded_services": "💰 SGD 4 per person per day for Guide & Driver Tipping",
    "important_notes": "Arrive at HarbourFront Centre 90 minutes before ferry departure.",
    "tags": ["Batam", "Seafood", "Short Trip"],
    "days": [{"day_number": 1, "day_title": "...", "content": "..."},
             {"day_number": 2, "day_title": "...", "content": "..."}],
}
r = requests.post(f"{BASE}/tour/products/api/upsert", json=payload, headers=H, timeout=60).json()
pid = r["product_id"]

with open("cover.jpg", "rb") as f:
    requests.post(f"{BASE}/tour/products/{pid}/upload-image", headers=H,
                  data={"kind": "cover"}, files={"image": f}, timeout=120)

gallery = [("image", open(p, "rb")) for p in ["01.jpg", "02.jpg"]]
requests.post(f"{BASE}/tour/products/{pid}/upload-image", headers=H,
              data={"kind": "gallery"}, files=gallery, timeout=300)

print(requests.get(f"{BASE}/tour/products/{pid}/json", headers=H).json()["product"]["product_status"])
```

---

## 8. 批量时的汇报格式（建议）

处理完一批后给人一张表，方便逐个审核：

| 文件夹 | 结果 | 产品 id / 编号 | 缺失 / 推断 | warnings |
|---|---|---|---|---|
| Batam Lobster 2D1N | created (draft) | 259 / BTM-LOBSTER-2D1N | 缺价格、有效期；城市/天数为推断 | 无封面 |

人审核通过后，可一次性上架：逐个 `POST /tour/products/<pid>/patch {"product_status":"active"}`。
