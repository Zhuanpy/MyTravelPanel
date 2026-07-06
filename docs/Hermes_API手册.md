# Hermes API 手册（当前可用接口清单）

面向 Hermes agent / 脚本，通过 **API Token（X-API-Key）** 无状态调用后端。
本手册只收录**当前已经是 JSON、agent 可直接调**的接口，按任务组织。
文末「尚不可用」列出还停留在表单/HTML、需要另补 JSON 接口的动作，供边界参考。

> 初版为盘点整理，生成日期 2026-07-02。
> 最后更新 2026-07-06：新增「按姓名反查项目」接口 `/projects/list/api/search-by-person`（见 §8）。

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

## 1. 机票下单（核心闭环，已打通）

标准流水线：**复制项目 → 重建人员 → 删旧REF → 一键建 REF+EO+发票**。

| 步骤 | 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|---|
| 复制项目 | `/projects/detail/<source_id>/copy` | POST | JSON/空 | 返回 `new_project_id / new_hid / new_ref_ids` |
| 读成员 | `/projects/<pid>/members` | GET | — | 返回 `data[]`（含 id） |
| 删成员 | `/projects/<pid>/members/<mid>` | DELETE | — | 逐个删 |
| 批量加成员 | `/projects/<pid>/members/batch` | POST | JSON | 首个自动设 Leader |
| 删旧REF | `/projects/ref/delete/<rid>?format=json` | POST | — | 删复制来的旧 REF |
| **一键建单** | `/projects/ref/flight/quick-create/<pid>` | POST | JSON | 建机票 REF + EO + 发票 |

**一键建单请求体**：
```json
{
  "supplier_id": 256,
  "remarks": "ZHOU 机票订单",
  "leader_name": "ZHOU YONGFA",
  "passengers": [
    {"name": "ZHOU YONGFA", "type": "adult", "selling_price": 255, "cost_price": 224.2,
     "passport_number": "E12345678"}
  ],
  "segments": [
    {"flight_number": "HU448", "cabin_code": "Y",
     "departure_airport": "SIN", "arrival_airport": "HAK",
     "departure_date": "2026-07-03", "departure_time": "04:40",
     "arrival_date": "2026-07-03", "arrival_time": "08:25"}
  ],
  "auto_eo": true,
  "auto_invoice": true
}
```
返回：`{ref_id, ref_number, eo_number, invoice_number, eo_error?, invoice_error?}`。

**批量加成员请求体**：
```json
{"members": [{"member_name": "ZHOU YONGFA", "member_name_en": "ZHOU YONGFA"}]}
```

### 机票改单（字段级，无需删重建）
| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/projects/ref/flight/<rid>/segments` | GET | — | 航段列表（先拿 id） |
| `/projects/ref/flight/segment/<sid>/update` | POST | JSON | 改单个航段字段（航站楼/时刻/票号等） |
| `/projects/ref/flight/<rid>/passengers` | GET | — | 乘客列表 |
| `/projects/ref/flight/passenger/<pid>/update` | POST | JSON | 改单个乘客字段 |

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

## 10. 产品 / 预算

| 接口 | 方法 | 入参 | 说明 |
|---|---|---|---|
| `/staff/products/api/list` | GET | query | 统一产品列表 |
| `/staff/products/api/detail/<id>` | GET | — | 产品详情 |
| `/staff/products/api/categories` `/api/stats` | GET | — | 分类/统计 |
| `/tour/products/<id>/price-variants` | GET | — | 旅游产品价格变体 |
| `/package_budget/<bid>/export` | GET | — | 预算单导出 JSON |
| `/package_budget/project/<pid>/json` | GET | — | 项目关联预算单 JSON |

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
