# 护照 OCR 接口（供 Hermes / 脚本调用）

面向非浏览器客户端（Hermes agent、curl、requests）的护照识别接口说明。
全程用 **API Token（X-API-Key）** 无状态鉴权，无需登录、无需处理 CSRF。

- **Base URL**: `https://joyesc.com`（等价 `https://www.joyesc.com`；本地调试 `http://127.0.0.1:5000`）
- **鉴权**: 请求头 `X-API-Key: <token>`（也支持 `Authorization: Bearer <token>` 或 `?api_key=`）
- **权限**: token 绑定的用户必须是 **staff 角色**（`@staff_only`）。若返回被重定向到登录页，多半是 token 用户不是 staff。
- **生成 token**: `python scripts/20260622_manage_api_token.py create <邮箱> <标签>`

> 依赖前提：服务器需安装 OCR 组件——
> `apt install tesseract-ocr libgl1` + `pip install passporteye pytesseract Pillow`。
> 未安装时 `/ocr` 会返回 `服务器未安装 passporteye...`。

---

## 1. 识别护照 `POST /flights_passport/ocr`

图片 → MRZ OCR → JSON。**只识别，不落库。**

**请求**：`multipart/form-data`，字段名固定为 `image`（图片文件）。

- 支持格式：`png / jpg / jpeg / webp / bmp / tiff / tif`
- 单张 ≤ 10 MB

```bash
curl -X POST https://joyesc.com/flights_passport/ocr \
  -H "X-API-Key: $HERMES_TOKEN" \
  -F "image=@$HOME/.hermes/image_cache/passport_xxx.jpg"
```

```python
import requests

resp = requests.post(
    "https://joyesc.com/flights_passport/ocr",
    headers={"X-API-Key": HERMES_TOKEN},
    files={"image": open("/root/.hermes/image_cache/passport_xxx.jpg", "rb")},
    timeout=60,
)
data = resp.json()
```

**响应**（成功 HTTP 200）：

```json
{
  "success": true,
  "data": {
    "document_type": "P",
    "country_code": "CHN",
    "passport_number": "E12345678",
    "surname": "ZHANG",
    "given_name": "SAN",
    "nationality": "CHN",
    "date_of_birth": "19 NOV 1998",
    "sex": "M",
    "expiration_date": "20 NOV 2028",
    "personal_number": "",
    "mrz_raw": "P<CHN...\n...",
    "valid_score": 0
  }
}
```

- `date_of_birth` / `expiration_date` 已格式化为 `DD MON YYYY`。
- `sex`：`M` / `F`。
- `valid_score`：MRZ 校验位置信度，偏低说明识别可能有误，值得二次核对。

**失败**：

| HTTP | 场景 | 响应 |
| ---- | ---- | ---- |
| 400 | 没传图片 / 格式不支持 / 超过 10 MB | `{"success": false, "error": "..."}` |
| 422 | 图里没检测到 MRZ 机读码 | `{"success": false, "error": "未检测到护照 MRZ 区域..."}` |
| 500 | 服务异常 / 未装依赖 | `{"success": false, "error": "..."}` |

---

## 2. 存入常用旅客表 `POST /flights_passport/save`

把识别结果写入 `frequent_travelers`（常用旅客），**去重键 = 护照号**。

**请求**：`application/json`。字段与 `/ocr` 的 `data` 基本一一对应，可直接把上一步的
`data` 透传（多余字段会被忽略）。

| 字段 | 必填 | 说明 |
| ---- | ---- | ---- |
| `surname` | ✅ | 姓 |
| `given_name` | ✅ | 名 |
| `passport_number` | ✅ | 护照号（去重键） |
| `nationality` |  | 国籍 |
| `sex` |  | `M` / `F` |
| `date_of_birth` |  | `DD MON YYYY` 或 `YYYY-MM-DD` |
| `expiration_date` |  | 护照有效期，同上格式 |
| `country_code` |  | 签发国（写入 `passport_issuing_country`） |
| `title` |  | 称谓 `MR/MS/MISS/MASTER`；不传则按性别+年龄自动推断 |
| `name` |  | 中文姓名 |
| `group_name` |  | 集团/分组 |
| `merge_into_id` |  | 见下方「重名去重」 |
| `force_create` |  | 见下方「重名去重」 |

**去重行为**：

1. 护照号已存在 → 更新那条，`action = "updated"`
2. 传了 `merge_into_id` → 合并进指定旅客，`action = "merged"`
3. 否则新建，`action = "created"`

**成功响应**：

```json
{ "success": true, "action": "created", "data": { "...同 /ocr 的字段..." } }
```

**重名待确认**（发现同名、但没护照号的疑似同一人，需人工决定合并还是新建）：

```json
{
  "success": false,
  "need_resolution": true,
  "candidates": [
    { "id": 88, "traveler_code": "T0088", "name": "张三",
      "name_en": "ZHANG SAN", "phone": "138...", "company_name": "XX公司" }
  ]
}
```

处理方式（二选一，重新 POST 一次）：
- 合并进某条：body 加 `"merge_into_id": 88`
- 强制新建：body 加 `"force_create": true`

---

## 3. 识别 → 入库 一步到位（Hermes 推荐用法）

```python
import requests

BASE = "https://joyesc.com"
H = {"X-API-Key": HERMES_TOKEN}

# 1) 识别
r = requests.post(f"{BASE}/flights_passport/ocr", headers=H,
                  files={"image": open(img_path, "rb")}, timeout=60)
r.raise_for_status()
ocr = r.json()
if not ocr.get("success"):
    raise RuntimeError(ocr.get("error"))

# 2) 入库（OCR 的 data 直接透传）
payload = dict(ocr["data"])
s = requests.post(f"{BASE}/flights_passport/save", headers=H,
                  json=payload, timeout=30).json()

# 3) 若命中重名，二次确认
if s.get("need_resolution"):
    payload["force_create"] = True          # 或 payload["merge_into_id"] = 候选id
    s = requests.post(f"{BASE}/flights_passport/save", headers=H,
                      json=payload, timeout=30).json()

print(s["action"], s["data"]["traveler_code"])
```

> 上传护照原图存档（可选）：`POST /flights_passport/save_image`，`multipart` 带 `image`
> + 与 `/save` 相同的护照字段，会 find-or-create 旅客并把图片挂到该旅客的 `traveler_files`。
