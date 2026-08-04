# Hermes API 手册（当前可用接口清单）

面向 Hermes agent / 脚本，通过 **API Token（X-API-Key）** 无状态调用后端。
本手册只收录**当前已经是 JSON、agent 可直接调**的接口，按任务组织。
文末「尚不可用」列出还停留在表单/HTML、需要另补 JSON 接口的动作，供边界参考。

> 初版为盘点整理，生成日期 2026-07-02。
> 2026-07-06：新增「按姓名反查项目」接口 `/projects/list/api/search-by-person`（见 §8）。
> **最后更新 2026-07-27**：鉴权失败改返回 401/403 JSON（不再 302 到登录页）；
> 新增 `whoami` 自检、`companies/search` 查公司、`order/<hid>/summary` 验收；
> `copy` 支持 `with_refs:false`；`quick-create` 支持 `idempotency_key`。见 §0.1 与 §1。

---

## 0. 通用约定

- **Base URL**：`https://joyesc.com`（本地 `http://127.0.0.1:5000`）
- **鉴权**：请求头 `X-API-Key: <staff token>`（也支持 `Authorization: Bearer`）。
  - token 走 Flask-Login request_loader → 免登录；带 token 的请求自动跳过 CSRF。
  - 绝大多数写接口在 staff 角色下可用（`@staff_only`）。
- **生成 token**：`python scripts/20260622_manage_api_token.py create <邮箱> <标签>`
- **返回约定**：成功一般 `{"success": true, ...}`；失败 `{"success": false, "error"/"message": "..."}`。
- **入参形态**：标注 `JSON` 用 `Content-Type: application/json`；标注 `form` 用表单编码；标注 `files` 用 multipart。
- **参考脚本**：`scripts/20260701_create_order_via_api.py`（完整下单流水线，权威示例）。

### 自描述接口（Hermes 开机 fetch 一次即可拿到最新清单）
- `GET /api/hermes/catalog` —— 结构化 JSON 接口目录（含分组、路径、入参、说明），agent 好解析。
- `GET /api/hermes/manual` —— 返回本手册 markdown 全文（运行时读取，始终最新）。
- 二者都走 token 鉴权。Hermes 记忆里只需存「去 `/api/hermes/catalog` 拿清单」一句，不必记全文。

---

## 0.1 鉴权失败怎么办（**必读，不要猜**）

**2026-07-27 起**：带 token / `/api/` 路径 / `Accept: application/json` 的请求，
鉴权失败会返回明确的 **401 / 403 JSON**，不会再 302 到登录页。
（此前一律 302，agent 拿到登录页 HTML 只能靠猜，容易误判成「token 过期」。）

| 状态码 | 含义 | 正确动作 |
|---|---|---|
| **401** `unauthorized` | token 缺失 / 无效 / 已停用 | **停止并报告**，等人换 token |
| **403** `forbidden_role` | token 有效，但账号角色不是 staff | **停止并报告**，换 token 也没用 |
| 其它 4xx/5xx | 与鉴权无关（路径、参数、数据权限） | 原样报出状态码 + 响应体，**不要**当成鉴权问题 |

**自检探针**：`GET /api/hermes/whoami`

遇到任何疑似鉴权失败，先打这里，再决定下一步：

- **200** → token 有效。故障在刚才那个请求本身，把状态码和响应体原文报出来。
- **401 / 403** → 按上表处理。

> ⚠️ **`ApiToken` 没有过期时间**（模型只有 `is_active` 开关）。
> 所以「token 过期了」这个判断**永远是错的**。token 失效只可能是被停用、
> 账号被禁用，或请求根本没带上 header。
>
> ⚠️ **任何情况下都不要降级到「用账号密码登录浏览器」**。
> 那会把凭证写进日志，且掩盖真实故障。宁可停下来报错。

---

## 0.2 查公司（下单前第一步）

`GET /api/hermes/companies/search?q=LEZE`

| 参数 | 说明 |
|---|---|
| `q` | 必填。匹配公司名 / 简称 `alias` / 公司代码 `company_code` |
| `limit` | 默认 20，上限 50 |
| `role` | `customer`（默认）/ `supplier` / `any` |

返回 `data[]`，每项含 `id`（即下单要用的 `company_id`）、`company_name`、`alias`、
`currency`，以及 `contacts[]` 联系人列表（含姓名/职位/电话/邮箱/是否主要联系人）。
按使用热度排序，常用公司排前面。

> 用它替代「开浏览器搜公司」——一次请求拿到公司 ID 和联系人。

---

## 1. 机票下单（核心闭环，已打通）

标准流水线：**复制项目 → 重建人员 → 删旧REF → 一键建 REF+EO+发票**。

| 步骤 | 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|---|
| 0. 查公司 | `/api/hermes/companies/search?q=` | GET | — | 拿 `company_id` + 联系人 |
| 1. 复制项目 | `/projects/detail/<source_id>/copy` | POST | `{with_refs:false, company_id, contact}` | **三个参数一起传**，见下 |
| 2. 读成员 | `/projects/<pid>/members` | GET | — | 返回 `data[]`（含 id） |
| 3. 删成员 | `/projects/<pid>/members/<mid>` | DELETE | — | **先删干净**，逐个删 |
| 4. 批量加成员 | `/projects/<pid>/members/batch` | POST | JSON | **删空后再加**，首个自动设 Leader |
| 5. **一键建单** | `/projects/ref/flight/quick-create/<pid>` | POST | JSON | 建 REF + EO + 发票，**行李一起传** |
| 6. **验收** | `/api/hermes/order/<hid>/summary` | GET | — | 逐项比对，见 §1.1 |

**复制这一步要一次做完三件事（2026-07-27 更新）**

```json
POST /projects/detail/<模板项目id>/copy
{
  "with_refs": false,        // 不复制模板 REF/航段/乘客
  "company_id": 69,          // 改成本单客户（模板多半属于别的客户！）
  "contact": "ZHENXIANG"     // 本单联系人
}
```

三件事缺一不可：

1. **`with_refs: false`** —— 模板 REF 对新订单毫无用处。不传的话会复制过来，
   得靠「建完新单再回头删」收场，顺序颠倒且中途失败会留脏数据。
2. **`company_id`** —— **模板项目属于哪个客户，复制出来就还是哪个客户**。
   不覆盖的话，给 SIONG 下的单会挂在 KATONG 名下。这是最容易漏的一步。
3. **`contact`** —— 同理，联系人也会跟着模板走。

其它可覆盖字段：`desc` / `currency` / `leader_name` / `dept`。
`company_id` 不存在时接口直接返回 400，不会建出挂错公司的项目。

返回体回显 `company_id` / `company_name` / `contact` / `applied_overrides`，
**复制完就能立刻断言客户对不对**，不用再 GET 一次。

> 老流程仍然可用：不传这些参数即保持原行为（复制 REF、沿用模板客户），
> 返回的 `new_ref_ids` 就是复制来的 REF。但自动化下单一律传全三个参数。

**换乘客必须「先删后加」，顺序反了会留旧 Leader（2026-08-04 新增）**

copy 会把模板项目的 `header.leader_name` 和成员的 `is_leader` **一起抄到新项目**。
所以第 3 步（删）必须排在第 4 步（加）**前面**：

- ✅ 先 `DELETE` 掉所有旧成员 → 再 `POST /members/batch` 加新人。
  项目此刻为空，新成员天然是首个成员，`is_leader` 与 `header.leader_name` 一并自动写好，
  **零额外请求**。
- ❌ 先加后删：`add_member` 只在项目**一个成员都没有**时才自动设 Leader，
  而 `DELETE` 既不改选 Leader 也不动 `header.leader_name` →
  新项目挂着上一单的人名，项目列表 / 详情 / summary 显示的全是错的。
  （2026-08-04 H2163、H2164 连续两单因此显示 "UDDIN MD MAIN"。）

**兜底：`POST /projects/<pid>/members/<mid>/set-leader`** —— 纯 JSON 接口，
`@csrf.exempt` + token 直通，会同时设 `is_leader` 并同步 `header.leader_name`。

> ⚠️ **这个接口一直存在，不要以为「没有成员更新 API」就降级去开浏览器点按钮。**
> 成员的增删改查全是 JSON（见 §附录 `/projects/<pid>/members`）。
> 任何时候都不要在自动化流程里输入账号密码 —— 密码会被打进日志。
> 怀疑鉴权有问题，先调 `GET /api/hermes/whoami` 自检，200 就说明 token 没事。

> `quick-create` 里的 `leader_name` 只写进 `ref.extra_info` 供**发票打印**用，
> **设计上不回写项目头**，指望它纠正 Leader 是无效的。

**一键建单请求体**：
```json
{
  "supplier_id": 256,
  "remarks": "ZHOU 机票订单",
  "leader_name": "ZHOU YONGFA",
  "passengers": [
    {"name": "ZHOU YONGFA", "type": "adult", "selling_price": 255, "cost_price": 224.2,
     "passport_number": "E12345678",
     "baggage": "40KG"}
  ],
  "segments": [
    {"flight_number": "HU448", "cabin_code": "Y",
     "departure_airport": "SIN", "arrival_airport": "HAK",
     "departure_date": "2026-07-03", "departure_time": "04:40",
     "arrival_date": "2026-07-03", "arrival_time": "08:25"}
  ],
  "auto_eo": true,
  "auto_invoice": true,
  "idempotency_key": "hermes-<订单来源消息ID>"
}
```
返回：`{ref_id, ref_number, eo_number, invoice_number, eo_error?, invoice_error?}`。

**行李在这里一次传完，不要事后补**

`passengers[].baggage` 就是行李额（写入乘客级默认值，所有航段共用）。
建单时一起传即可，**不需要**建完再调 `ticketing` / `passenger/update` 补一遍。

只有「同一乘客不同航段行李额不同」时，才需要用 `passengers[].segments[].baggage`
分航段覆盖——那也是同一个请求里传完。

> 事后补行李 = 多一次请求 + 多一个失败点 + 中间态数据不完整。

**`idempotency_key`（2026-07-27 新增，强烈建议必传）**

同一笔订单**固定不变**的字符串（≤64 字符），例如 `hermes-<来源消息ID>`，
或 `<hid>-<乘客名>-<航班号>-<日期>` 的哈希。

- 首次请求正常建单，并把 key 记在 REF 上。
- 重试 / 超时重发 / 网络抖动导致的重复请求，**原样返回首次结果**，
  额外带 `"idempotent_replay": true`，不会再建一个 REF。
- 不传则无保护——重复 POST 会实打实建出两个 REF（各带一份 EO + 发票）。

> 重试时必须复用**同一个 key**。每次重试都换新 key = 没有幂等保护。

### 1.1 下单验收（`GET /api/hermes/order/<hid|pid>/summary`）

一次返回项目的全部关键事实，供逐项断言，不必自己调 4 个接口拼装。

返回顶层：`hid / company_id / company_name / contact / leader_name / currency / status /
ref_count / refs[]`；每个 ref 含 `ref_number / supplier_id / supplier_name /
selling_price / cost_price / eo_number / invoice_number / passengers[] / segments[]`。

**字段形态与 `quick-create` 入参一致，可直接比对**（2026-07-27 调整）：
`segments[]` 里给的是 `departure_date: "2026-07-29"` + `departure_time: "18:40"`
**分离字段**，和下单入参同形；完整 ISO 值另存在 `departure_datetime_iso`。

> ⚠️ 早期版本这里返回的是 ISO 全量 `departure_time: "2026-07-29T18:40:00"`，
> 断言时得自己拆——那本身就是出错来源。已改为分离字段。
> 如果你的断言按 ISO 写的，**要跟着改**。

**验收规则**：拿它与**解析阶段得到的原始订单要素**逐项比对——
乘客姓名、护照号、航班号、起降机场、日期时间、售价、成本、供应商 ID、行李，
以及项目头三项：**`leader_name`**、`company_name`、`contact`。
全部一致才算成功；任何一项不符，原样列出「期望 vs 实际」，**不要自行修补**。

> ⚠️ **`leader_name` 必查**：它是项目列表/详情实际显示的那个名字，
> 复制模板时会带着旧人名过来，REF 乘客对不代表它对。
> 断言它 == 本单乘客（多人时为 leader），不等就是第 3/4 步顺序反了，见上文。

> ⚠️ 必查 `ref_count`：正常单 REF 订单应为 **1**。多出来说明重复建单，
> 或模板 REF 没清干净（这正是 `with_refs:false` 要解决的问题）。

**批量加成员请求体**：
```json
{"members": [{"member_name": "ZHOU YONGFA", "member_name_en": "ZHOU YONGFA"}]}
```

### 机票改单（字段级，无需删重建）
| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/ref/flight/<rid>/segments` | GET | — | 航段列表（先拿 id） |
| `/projects/ref/flight/segment/<sid>/update` | POST | JSON | 改单个航段字段（航站楼/航司/舱位）。**不含 PNR/票号/座位/行李** |
| `/projects/ref/flight/<rid>/passengers` | GET | — | 乘客列表（含 segments 格子数组） |
| `/projects/ref/flight/passenger/<pid>/update` | POST | JSON | 改单个乘客的默认值 + 各航段格子 |
| `/projects/ref/flight/<rid>/ticketing` | POST | JSON | **补行程单首选**：一个请求灌完整个 REF 的票务矩阵 |

> ⚠️ **PNR / 票号 / 座位 / 行李 是「乘客×航段」级**，存在 `project_flight_passenger_segments`
> 交叉表里。格子留空 = 继承乘客级默认值（座位除外，座位没有默认值）。
> **不要**用 segment/update 写这四个字段——航段表上的同名字段已废弃，写了也不显示。

**补行程单（推荐流程）**：先 `GET /flight/<rid>/segments` 拿航段 id，再一次性写完：

```json
POST /projects/ref/flight/<rid>/ticketing
{
  "replace": false,
  "passengers": [
    {
      "name": "HONG YING",
      "pnr": "ABC123",
      "ticket_number": "784-1234567890",
      "baggage": "23KG",
      "passport_number": "E12345678",
      "segments": [
        {"segment_id": 1664, "seat": "12A"},
        {"segment_id": 1665, "seat": "3C", "pnr": "ZZZ999", "baggage": "30KG"}
      ]
    }
  ]
}
```
- 乘客可用 `name`（大小写/首尾空格不敏感）或 `passenger_id` 指定；同名多人时必须用 id
- `segments` 里留空的字段继承上面的乘客级默认值；座位没有默认值，必须逐段写
- `replace: true` = 先清空这些乘客的所有旧格子再写（整份覆盖，用于重新出票/改签后重灌）
- 任一乘客出错整批回滚，不会写一半

**单个乘客微调**（改一个座位这种）：`POST /flight/passenger/<pid>/update`
- 乘客级默认值：`{"pnr": "ABC123", "ticket_number": "784-...", "baggage": "23KG"}`
- 分航段覆盖：`{"segments": [{"segment_id": 123, "seat": "53K"}]}`
- 单段简写：`{"segment_id": 123, "seat": "53K"}`
- 格子字段传 `null` 或 `""` = 清空覆盖值，回落到乘客级默认值（四项全清则该行格子自动删除）

---

## 2. 护照 / 常用旅客

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/flights_passport/ocr` | POST | files `image` | 护照图片 → MRZ → JSON（不入库） |
| `/flights_passport/save` | POST | JSON | 识别字段落库常用旅客（去重键=护照号） |
| `/flights_passport/save_image` | POST | files+form | 存护照图并 find-or-create 旅客 |
| `/flights_passport/recent` | GET | query `q,page,limit` | 近期护照旅客列表 |
| `/projects/frequent_traveler/api/list` | GET | query | 旅客列表 |
| `/projects/frequent_traveler/api/search` | GET | query `q` | 旅客搜索 |
| `/projects/frequent_traveler/api/create` | POST | JSON | 建旅客 |
| `/projects/frequent_traveler/api/<tid>` | GET/PUT/DELETE | JSON | 查/改/删旅客 |

> 详见 `docs/护照OCR接口_Hermes.md`。
> ⚠️ `frequent_traveler/api/*` 目前**未挂鉴权装饰器**，无 token 也可能可调（安全项，见文末）。

---

## 3. 实时航班 & 行程/单据解析（agent 最爱的读侧工具）

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/get-flight-info` | GET | query `flight_number,dep_iata,arr_iata,flight_date` | **实时抓航班**（Aerodatabox→FR24→DB 三级回退，含航站楼/登机口） |
| `/api/flight_info/<flight_number>` | GET | path | FR24 实时航班信息 |
| `/search_airports` | GET | query `iata,city` | 机场模糊搜索 |
| `/flights_booking/parse_flight_text` | POST | JSON `text` | 粘贴行程文字 → 结构化航段/乘客 |
| `/flights_booking/parse_flight_image` | POST | JSON `image,platform` | 截图 OCR → 航段 |
| `/flights_athina/parse_flights` | POST | JSON `text` | 解析 Trip/携程/Google Flights/酷航 行程 → 航段（对应 conversion 页「航班解析」标签） |
| `/flights_athina/api/convert_itinerary` | POST | JSON `text,language,luggage,price` | 行程文本 → 格式化中/英文行程单（对应「机票行程转换」标签） |
| `/flights_athina/generate_booking_code` | POST | JSON `[{flightNumber,flightDate}]` | 生成 GDS 订位指令串（对应「ATHINA代码生成」标签，**非真实预订**） |
| `/flights_usbangla/parse_pdf` | POST | files `pdf_file` | 解析 US-Bangla 电子票 |
| `/flights_usbangla/parse_mu_pdf` `/parse_tongcheng_pdf` `/parse_text_itinerary` | POST | files/JSON | 东航/同程/文本行程解析 |
| `/ocr_flight_info` | POST | files `file` | 航班信息图片 OCR |

> ⚠️ athina/usbangla/booking 里**没有真实自动预订**能力，只有查询/解析/生成订位串。
> ⚠️ `/flights_athina/conversion?tab=parse|itinerary|athina` 是**页面路由**（渲染工具页 HTML），
> 不要当 API 调；三个标签的实际能力就是上表对应的三个 POST 接口。

---

## 4. 发票

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/invoice/header/<hid>/quick-create` | POST | JSON | 选 REF 快速开发票 |
| `/projects/invoice/quick_create/<pid>` | POST | JSON | 按项目快速开发票 |
| `/projects/invoice/<iid>/sync-ref-prices` | POST | — | 同步 REF 价格到发票 |
| `/projects/invoice/void` | POST | JSON | 按发票号作废 |
| `/projects/invoice/find_by_number` | POST | JSON | 按号查发票 |
| `/projects/invoice/<iid>/send` | POST | JSON | 发送发票邮件 |
| `/projects/invoice/<iid>/cancel` | POST | — | 取消发票 |
| `/projects/invoice/<iid>/tags` | POST | JSON | 改发票标签 |
| `/projects/invoice/api/header/<hid>/summary` | GET | — | 发票汇总 |

---

## 5. EO（订单执行单）/ 付款

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/eo/quick_create/<rid>` | POST | JSON/空 | 快速创建 EO |
| `/projects/eo/<eid>/update` | POST | JSON | 改 EO |
| `/projects/eo/<eid>/pay` | POST | JSON | 单 EO 付款 |
| `/projects/eo/<eid>/void` | POST | JSON/空 | 作废 EO |
| `/projects/eo/<eid>/cancel_payment` | POST | — | 取消 EO 付款 |
| `/projects/eo/batch-pay/generate-payment-no` | GET | — | 生成付款号 |
| `/projects/eo/batch-pay/validate-eos` | POST | JSON | 校验 EO 可付 |
| `/projects/eo/batch-pay/submit` | POST | JSON | 批量付款提交 |
| `/projects/payment/<pmid>/cancel` | POST | — | 取消付款 |
| `/projects/payment/<pmid>/reconcile` | POST | JSON | 对账开关 |
| `/projects/payment/api/summary` | GET | query | 付款汇总 |

---

## 6. 预付账款（Prepayment）

> 「创建」目前仍是表单（见文末缺口），但确认/使用/取消等后续动作已是 JSON。

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/prepayment/<ppid>/confirm` | POST | — | 确认预付 |
| `/projects/prepayment/use` | POST | JSON | 使用预付账款 |
| `/projects/prepayment/<ppid>/reconcile` | POST | JSON | 对账开关 |
| `/projects/prepayment/<ppid>/cancel` `/delete` | POST | — | 取消/删除 |
| `/projects/prepayment/api/supplier/<sid>/prepayments` | GET | — | 供应商可用预付 |
| `/projects/prepayment/api/summary` | GET | query | 预付汇总 |

---

## 6.5 退款收退跟踪（Refund Tracking）

> 退款单的「创建」仍是表单（见文末缺口），但两条跟踪线已是 JSON：
> 供应商有没有把钱退给我们、我们有没有把钱退给客户。

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/refund/<refund_id>/tracking` | POST | JSON（局部更新） | 更新收退款跟踪状态 |

只传需要改的字段即可，未传字段保持原值：

```json
{
  "supplier_name": "Scoot",
  "supplier_refund_status": "received",   // pending / partial / received / na
  "supplier_refund_amount": "1200.00",
  "supplier_refund_date": "2026-07-20",
  "supplier_refund_remarks": "已到账",
  "customer_refund_status": "paid",       // pending / partial / paid
  "customer_refund_amount": "1200.00",
  "customer_refund_date": "2026-07-22",
  "customer_refund_remarks": "转账尾号1234"
}
```

返回 `{success, message, refund}`，`refund` 为整单 JSON（含明细）。
列表页可用 `?supplier_status=pending` / `?customer_status=pending` 筛出待办。

---

## 7. 结算 / 利润分配

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/list/api/settle/<pid>` `/api/unsettle/<pid>` | POST | — | 结算/取消结算单个项目 |
| `/projects/settlement/api/batch_settle` `/api/batch_unsettle` | POST | JSON | 批量结算 |
| `/projects/settlement/api/preview_voucher_no` | GET | — | 预览凭证号 |
| `/projects/settlement/api/calculate_profit_distribution` | POST | JSON | 计算利润分配 |

---

## 8. 项目读侧 / 成员 / 提醒 / 文件

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/detail/<pid>/refs` | GET | — | 项目 REF 列表 |
| `/projects/detail/<pid>/stats` | GET | — | 项目统计 |
| `/projects/detail/<pid>/receipts` `/payments` `/documents` | GET | — | 收款/付款/文档列表 |
| `/projects/detail/<pid>/copy` | POST | JSON | 复制项目 |
| `/projects/detail/<pid>/email/send` | POST | form+files/JSON | 发项目邮件（带附件） |
| `/projects/list/api/stats` `/api/quick-filter/<t>` | GET | query | 项目统计/快捷筛选 |
| `/projects/list/api/search_companies` | GET | query `q` | 搜索客户公司 |
| `/projects/list/api/search-by-person` | GET | query `q,limit?` | **按姓名反查项目**：命中联系人/负责人/REF乘客/项目成员，返回结构化列表 |
| `/projects/<pid>/members` (+`/batch` `/<mid>` `/set-leader`) | GET/POST/PUT/DELETE | JSON | 成员管理（全 JSON） |
| `/projects/reminder/<hid>/list` (+`create/update/delete/toggle`) | GET/POST | JSON | 项目提醒（全 JSON） |
| `/projects/file/<hid>/files` (+`upload/download/delete`) | GET/POST | files/JSON | 项目文件 |
| `/projects/header/update_desc` `/update_company` `/update_status` `/update_contact` `/update_remarks` | POST | JSON | header 字段级改（⚠️无鉴权装饰器） |

**按姓名反查项目** `GET /projects/list/api/search-by-person?q=ZHANG+SHIBIN&limit=50`

用姓名一次查出「这个人在哪些项目/REF 里出现过」，免去解析列表页 HTML。命中四类来源合并返回，用 `role` 区分：

- `passenger` —— REF 乘客（机票），带 `ref_number` 与该 REF 的 `selling_price`/`ref_status`
- `member` / `leader` —— 项目成员（`is_leader` 为 leader）
- `contact` —— 项目联系人（Header.contact）
- `leader` —— 项目负责人（Header.leader_name）

返回示例：
```json
{
  "success": true,
  "query": "ZHANG SHIBIN",
  "count": 1,
  "data": [
    {
      "project_id": 3267,
      "hid": "H1962",
      "ref_number": "R2596",
      "description": "06AUG-18AUG SIN-YVR-SIN",
      "company_name": "CHEN LI",
      "matched_name": "ZHANG SHIBIN",
      "role": "passenger",
      "status": "active",
      "ref_status": "confirmed",
      "selling_price": 11700.00,
      "created_at": "2026-07-03T13:03:50"
    }
  ]
}
```

> 项目级命中（member/leader/contact）无对应单一 REF，`ref_number`/`selling_price`/`ref_status` 为 `null`，`description` 取项目描述。`limit` 为每类来源上限（默认 50）。

---

## 9. 签证（读+材料+填表已可用）

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/visa/project/generate_form/<id>` | POST | — | 生成韩国签证表格（自动填表）※见下方注意 |
| `/visa/project/create_project_links/<id>` | POST | — | 自动建 HID + REF 关联 |
| `/visa/project/sync_project_documents/<id>` | POST | — | 从模板同步资料清单 |
| `/visa/project/save_document_status` | POST | JSON | 批量保存资料准备状态 |
| `/visa/project/get_document_status/<id>` | GET | — | 读资料准备状态 |
| `/visa/project/add_custom_document/<id>` | POST | JSON | 加自定义资料项 |
| `/visa/project/api/files/<pid>` | GET | — | 项目材料文件列表 |
| `/visa/project/api/files/<pid>/upload` | POST | files+form | **上传签证材料**（agent-ready） |
| `/visa/project/api/files/bulk_download` | POST | JSON `file_ids` | 打包下载 |
| `/visa/project/coordinates/save` `/add` `/delete/<id>` | POST | JSON | 填表坐标读写 |
| `/visa/documents/document_request/<visa_type>/<identity>` | GET | — | 某签证+身份所需资料 |
| `/visa/basic/api/get_visa_documents/<visa_type>` | GET | — | 签证文档配置 |

> ⚠️ **自动填表的重要限制**：`generate_form` 的申请人字段数据来自项目文件夹里的
> `FormSample.xls`（文件驱动），**没有 JSON 写入口**。坐标已入库、可通过 API 读写，
> 但「申请人填表数据」目前只能靠往文件夹丢 Excel —— 这是签证端到端自动化的主要断点。

---

## 10. 旅游项目 / 预算单（纯 JSON，已打通）

层级：`TourProject`（项目）→ `TourGroup`（团组）→ `TourItinerary`（每日行程）；
`BudgetHeader`（预算单）挂在项目下，`BudgetItem`（预算明细）挂在预算单下。

### 旅游项目

| 接口 | 方法 | 说明 |
|---|---|---|
| `/tour/projects/api/projects/<pid>` | GET | **先调这个**：项目全貌（项目+团组+每天行程，含所有 id） |
| `/tour/projects/api/projects` | POST | 新建项目（同时建第一个团组），返回 `project_id` / `group_id` |
| `/tour/projects/api/projects/<pid>` | POST | 局部更新项目（只改传入的字段） |
| `/tour/projects/api/projects/<pid>/groups` | POST | 给项目新增团组 |
| `/tour/projects/api/groups/<gid>` | POST | 局部更新团组 |
| `/tour/projects/api/groups/<gid>/itinerary` | POST | **批量灌行程**（补行程主力接口） |
| `/tour/projects/api/itinerary/<iid>` | POST | 局部更新单天行程 |

**批量灌行程**——一个请求把一份行程文案铺成 Day 1..Day N：

```json
POST /tour/projects/api/groups/<gid>/itinerary
{
  "replace": true,
  "days": [
    {"day_title": "Day 1: 抵达札幌", "date": "2026-09-01", "content": "<p>专车接机…</p>"},
    {"day_title": "Day 2: 小樽一日游", "content": "<p>小樽运河…</p>"},
    {"day_title": "Day 3: 富良野", "content": "<p>薰衣草田…</p>"}
  ]
}
```
- `date` 不填就按团组出发日 + 天序自动推算（第 N 天 = 出发日 + N-1 天），只有第一天要给
- `replace: true` = 先清空旧行程再写；默认 `false` 是追加
- 任一天出错整批回滚，不会留下半份行程
- 图片 `image1/2/3` 只接受**路径字符串**（素材库路径或已上传的相对路径）。要上传新图片文件，走 multipart 的 `/tour/projects/itinerary/create/<gid>`

**团组人数**：`pax` 是自动汇总的（= `adult_count` + `child_count`），不要直接写 `pax`。改团组人数会自动同步到关联的预算单。

### 预算单

| 接口 | 方法 | 说明 |
|---|---|---|
| `/package_budget/api/budgets/<bid>` | GET | 整张预算单（表头+明细+合计） |
| `/package_budget/api/projects/<pid>/quick-create` | POST | **幂等**按项目一键建单，已有则返回现有的 |
| `/package_budget/api/budgets` | POST | 新建预算单（可同时灌明细） |
| `/package_budget/api/budgets/<bid>` | POST | 更新表头（含 `target_currency` / `exchange_rate`） |
| `/package_budget/api/budgets/<bid>/items` | POST | 批量增明细（`replace: true` 可整份覆盖） |
| `/package_budget/api/budgets/<bid>/items/<iid>` | POST | 局部更新单条明细 |
| `/package_budget/api/budgets/<bid>/items/<iid>/delete` | POST | 删除单条明细 |

**预算明细有两条互斥的计价路径，选错小计就算错**：

```json
POST /package_budget/api/budgets/<bid>/items
{
  "replace": true,
  "items": [
    // person_based（默认）：adult_price / child_price × 人数
    {"category": "机票", "item_name": "新加坡-札幌往返",
     "pricing_method": "person_based", "adult_price": 800, "child_price": 600},

    // item_based：item_unit_price × item_quantity（与成人/儿童单价无关）
    {"category": "用车", "item_name": "9座商务车 7天",
     "pricing_method": "item_based", "item_unit_price": 350, "item_quantity": 7},

    // 进阶字段
    {"category": "酒店", "item_name": "札幌市区4晚",
     "pricing_method": "person_based", "adult_price": 480, "child_price": 240,
     "count_child_apply": false,      // 这项不算在儿童头上
     "adult_count_override": 2,       // 这项单独按 2 个成人算（不跟表头人数）
     "total_override": 1200,          // 直接覆盖小计：给了它，上面的单价×人数就不算了
     "is_optional": true, "remarks": "..."}
  ]
}
```

**最终货币换算**：表头的 `target_currency` + `exchange_rate` 决定。约定 `exchange_rate` = 1 SGD 兑多少 CNY；换算结果会**向上取整到 5 的倍数**（166→170）。返回里 `total_price` 是录入货币的原值，`total_price_final` 是换算后的值。

### 从供应商行程文档（.docx）导入项目

典型来源：地接社发来的报价行程单，一张大表格，每行一天，列是「日期 / 城市(抵达·离开) / 交通 / 旅游景点 / 餐食 / 酒店参考」，表格下面跟着报价、购物站、小费、团款包含、团款不含、其他备注。

**标准流程**：

1. `GET /tour/projects/api/projects/<pid>` —— **先读现状，做对撞检查**（见下方坑 2）
2. `POST /tour/projects/api/groups/<gid>` —— 写团组：日期、人数、`included_items` / `excluded_items` / `important_notes`
3. `POST /tour/projects/api/groups/<gid>/itinerary`（`replace: true`）—— 一次灌完整份每日行程

每天的 `content` 建议按「交通 / 景点 / 餐食 / 酒店」分行组织，比照搬表格单元格更适合网页展示：

```
交通：巴士
景点：雪乡风景区（含景区接驳车）、雪韵大街、大石碑…
注：雪乡倒站车无行李舱，建议小背包进入景区
餐食：B：酒店内享用　L：/　D：/
酒店：准四 — 雪韵假日酒店 或 忆山雪酒店 或同级
```

文档里的「团款包含 / 团款不含 / 小费 / 购物站 / 其他备注」分别落到团组的
`included_items` / `excluded_items` / `important_notes`（小费和购物站并进 `important_notes`）。

> ⚠️ **坑 1：报价格子可能是空的。** 很多报价单的价格表只有「2人 / RMB/人」的表头，
> 供应商还没填数字。**抽不到价格就把 `adult_price` / `child_price` 留空，并在回复里
> 明确说"文档未提供报价"** —— 不要瞎填，也不要默默跳过不提。价格没有就先别建预算单。

> ⚠️ **坑 2：日期必须和项目现有数据对撞检查。** 文档表格里的日期通常只有月/日
> （`D1 11/26`），年份得从文件名推（`20261126（2人小包）…docx` → 2026）。
> 更要命的是，**文档日期常常和项目里已有的出行日期不一致** —— 文档可能是供应商的
> 报价样板日期，而项目里存的是客人的实际出行日期。
> 发现不一致时**停下来问用户以哪个为准**，不要自己选一个覆盖过去。

> ⚠️ **坑 3：项目可能是从别的项目复制来的。** `folder_name` 带「(副本)」、或团组行程
> 与项目名对不上（比如项目叫「6D5N 哈尔滨」但挂着 8 天北京行程），说明是复制的空壳，
> 里面的 `group_code`、`operator`（地接社）也是从源项目带过来的**脏数据**。
> 这些字段文档里往往没有，不要凭空覆盖，但要在回复里提醒用户手动核对。

### 只读 / 其他

| 接口 | 方法 | 说明 |
|---|---|---|
| `/staff/products/api/list` `/api/detail/<id>` | GET | 统一产品列表 / 详情 |
| `/tour/products/<id>/price-variants` | GET | 旅游产品价格变体 |
| `/package_budget/<bid>/export` | GET | 预算单导出 JSON |
| `/package_budget/project/<pid>/json` | GET | 项目关联的预算单列表 |

> ⚠️ **不要用页面表单路由**（`/tour/projects/edit/<id>`、`/package_budget/<bid>/edit`、
> `/package_budget/<bid>/add_item` 等）。它们只收 form-encoded，成功后返回 302 重定向，
> 拿不到新建对象的 id，错误信息也只在 flash 里。一律用上面的 `/api/` 接口。

---

## 11. 打印 / PDF（HTML 页 + Chrome printToPDF）

发票和行程单**没有服务端 PDF 生成**，一直是浏览器把打印页转 PDF。Hermes 自带 Chrome，
所以直接复用：带 `X-API-Key` 导航到打印页 → 调 CDP `Page.printToPDF` 即得 PDF 字节。
打印 CSS（`@media print`）已隔离，只输出单据本身，nav/操作按钮不会进 PDF。

| 单据 | 打印页 | 方法 | 说明 |
|---|---|---|---|
| 发票 PDF | `/projects/invoice/<invoice_id>` | GET | 发票详情页；`@media print` 已强制只显示发票区（`#printInvoice`） |
| 行程单 PDF | `/flights_booking/print_itinerary/<ref_id>` | GET | 独立 A4 打印页（仅机票 REF 有航段/乘客） |

**Hermes 取 PDF 的步骤（CDP）**：
1. 用带 token 的 Chrome 导航到上述 URL（`X-API-Key` 通过 `Network.setExtraHTTPHeaders` 注入）。
2. 等页面加载完成，调用 `Page.printToPDF`（建议 `printBackground=true`、`preferCSSPageSize=true`）。
3. 返回的 base64 解码即 PDF 文件。

> 单页发票用 `@media print` 的绝对定位隔离即可；若遇到**多页发票**内容被截断，
> 再考虑加一个正常文档流的独立打印页（当前未做）。行程单页本就是独立文档流，不受影响。

---

## 12. 旅游产品库（Product Catalog：逐日行程 + 主体字段）

对应 `/tour/products/<pid>/edit` 页面。注意与第 10 节「旅游项目」不同：这里是**产品库**
（`Product` → `ProductItinerary` 每日行程），第 10 节是**具体项目/团**。全部 `@csrf.exempt`。

### 读侧（先读后改）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/tour/products/<pid>/json` | GET | **先调这个**：产品全量（主体字段 + 全部逐日行程，含 itinerary_id） |
| `/tour/products/<pid>/itineraries` | GET | 只列逐日行程（拿 itinerary_id 用） |
| `/tour/products/<pid>/itinerary/<iid>` | GET | 读单天行程 |

### 改产品主体字段（JSON body，局部更新）

```json
POST /tour/products/<pid>/patch          // Content-Type: application/json
{"base_price": 1288, "product_status": "active", "tags": ["亲子", "豪华"]}
```
- 只更新传入的字段，其余不动；返回 `{success, message, updated_fields, product}`
- 白名单：`product_name / product_code / base_price / child_price / infant_price /
  single_room_supplement / currency / duration_days / min_pax / max_pax /
  departure_city / destination_city / product_type / product_status /
  product_description / included_services / excluded_services / important_notes /
  suitable_season / difficulty_level / supplier_id / valid_from / valid_until /
  is_featured / tags（数组或逗号串）/ city_name（不存在自动建，可配 country_name）`
- `valid_from/valid_until` 用 `YYYY-MM-DD`；封面图 / 图库 / 供应商文件**不走此接口**

### 改逐日行程（form-data，非 JSON）

| 接口 | 方法 | 关键字段（multipart form-data） |
|---|---|---|
| `/tour/products/<pid>/itinerary/add` | POST | `day_number`(必填) `day_title` `content` `library_image1~3` 或上传 `image1~3` |
| `/tour/products/<pid>/itinerary/<iid>/update` | POST | 同上 |
| `/tour/products/<pid>/itinerary/<iid>/delete` | POST | — |
| `/tour/products/<pid>/itinerary/auto-assign-images` | POST | 自动从产品图库配图 |
| `/tour/products/<pid>/itinerary/import-excel` | POST | Excel 文件批量导入 |

> ⚠️ **主体走 JSON body，逐日行程走 form-data 字段**——两者格式不同别混。
> 逐日行程图片 `library_imageN` 只接路径字符串，上传新文件用 `imageN`（multipart）。

### 按公司批量维护产品（Hermes 主力入口）

> Hermes 用 token 调用时 **CSRF 自动豁免**；写接口带 `X-Requested-With: XMLHttpRequest` 或 `Accept: application/json`（或表单 `format=json`）即返回 JSON。

| 用途 | 方法 & URL | 说明 |
|---|---|---|
| **查产品**（文件名→id） | `GET /tour/products/lookup?supplier_id=<id>` | 该公司全部产品；也支持 `?code=<产品编号>` 精确、`?q=<关键词>` 名称模糊。返回 `{products:[{id, product_code, product_name, supplier_id, supplier_name, city_name, country, itinerary_count}]}` |
| **按公司导出** | `GET /tour/products/export/excel?supplier_id=<id>` | 导出该公司全部产品的 xlsx（也支持 `?ids=1,2,3`）。含 3 个 sheet |
| **批量导入/更新** | `POST /tour/products/import/excel` | multipart：`file`=xlsx，可选 `supplier_id`（供应商列空/没匹配时兜底赋给该公司），`format=json`。返回 `{imported, updated, price_imported, price_updated, itinerary_imported, itinerary_updated, errors}` |
| **灌逐日行程**（txt/Word 流） | `POST /tour/products/<pid>/itinerary/bulk` | JSON body，见下 |

**导入 Excel 三个 sheet**（导出的格式即导入模板，改完直接传回）：
- `产品数据`：`ID`(留空=新建) `供应商` `产品编号`(**upsert 主键**，空则自动生成) `产品名称`(必填) `产品类型` `国家` `城市` `出发城市` `目的地城市` `行程天数` `最少人数` `最多人数` `产品描述` `包含服务` `不包含服务` `重要提示` `标签` `产品状态` `有效期从` `有效期至`
- `价格方案`：按 `产品编号`+`方案名称` upsert（各房型售价/成本/货币/主要/启用）
- `每日行程`：按 `产品编号`+`天数` upsert（`标题`/`行程内容`）

**逐日行程 bulk（推荐给 txt/Word 流：Hermes 读文件→自己拆天→传结构化 JSON，服务端不硬解析 Word）**：
```json
POST /tour/products/<pid>/itinerary/bulk
{"replace": true, "days": [
  {"day_number": 1, "day_title": "抵达", "content": "专车接机…"},
  {"day_number": 2, "day_title": "游览", "content": "…"}
]}
```
- `replace: true`（默认）先清空该产品全部行程再建；`false` 按 `day_number` upsert
- 返回 `{success, created, updated, deleted}`

**典型批量流程**：`lookup?supplier_id` 拿到公司产品清单 → 用文件名/编号对应到 `product_id` → 主体信息走 `export→改→import/excel`（或逐条 `/patch`）→ 每个产品的 txt/Word 行程 `itinerary/bulk` 灌入。

---

## 尚不可用（当前只有 HTML/表单，需另补 JSON 接口才能给 Hermes）

按对「让 Hermes 干活」的价值排序：

1. **非机票 REF 下单** —— hotel / visa / tour / insurance / transport / attraction / other 只有
   `xxx/submit`（form→302），无 `quick-create` JSON。**只有机票能纯 API 下单。**
2. **签证端到端两断点** —— 建签证项目（form→redirect）+ 申请人填表数据无 JSON 写入口。
3. **REF 改单（非机票）** —— 只有机票有字段级 JSON，其余是 edit 表单。
4. **单笔收款创建** —— create 全是表单，只有批量发票收款是 JSON。
5. **退款 / 预付 创建** —— create/edit 表单（后续动作已 JSON）。
6. **项目 / Header 从零创建** —— 全表单。
7. **读侧结构化** —— 项目详情、机票订单列表、签证项目列表只有 HTML，无整单 JSON。

## 安全提醒（开放给 agent 前应处理）

以下动作类接口**未挂 `@login_required`/`@staff_only`**，当前无 token 也可能可调，
正式对外前建议补鉴权：`frequent_traveler/api/*` 全部、`project_header/update_*`、
`project_ref` 大量 detail/edit 与 `update_status`、`project_receipt` 前半段。
