# 签证REF创建模板字段分析报告

## 模板文件
`App_new/templates/business/projects/project_ref/create_visa_ref.html`

## 模型参考
`App_new/business/projects/models/ref.py` - `ProjectRef` 模型

---

## 字段对比分析

### ✅ 正确的字段

| 模板字段 | 模型字段 | 状态 | 说明 |
|---------|---------|------|------|
| `selling_price` | `selling_price` | ✅ | 匹配 |
| `cost_price` | `cost_price` | ✅ | 匹配 |
| `supplier_id` | `supplier_id` | ✅ | 匹配 |
| `status` | `status` | ✅ | 匹配 |
| `remarks` | `remarks` | ✅ | 匹配 |
| `country` | `extra_info` (JSON) | ✅ | 存储在 extra_info 中 |
| `visa_type` | `extra_info` (JSON) | ✅ | 存储在 extra_info 中 |
| `applicant_info` | `extra_info` (JSON) | ✅ | 存储在 extra_info 中 |

---

### ❌ 存在问题的字段

#### 1. `name` 字段 (第20行)
```html
<input type="hidden" name="name" id="auto_name" value="{{ ref.name if ref and not is_create else '' }}">
```

**问题**：
- ❌ 模型中没有 `name` 字段
- ✅ 模型中有 `description` 和 `detailed_description`
- ⚠️ 代码中通过 `request.form.get('description')` 处理，但模板提交的是 `name`

**影响**：
- 表单提交的 `name` 字段可能不会被处理
- 自动生成的名称可能丢失

**建议**：
- 删除 `name` 字段，或改为 `description`
- 或者路由中处理 `name` 并映射到 `description`

---

#### 2. `leader_name` 字段 (第101-105行)
```html
<input type="text" name="leader_name" class="form-control" required
       placeholder="请输入负责人姓名"
       value="{{ ref.leader_name if ref and not is_create else '' }}">
```

**问题**：
- ❌ `ProjectRef` 模型中没有 `leader_name` 字段
- ✅ `leader_name` 存在于 `ProjectHeader` 模型中（项目主表）
- ⚠️ 负责人应该保存在项目级别（HID），而不是REF级别

**分析**：
- 负责人信息应该统一保存在 `project_headers` 表中
- REF 可以通过 `ref.header.leader_name` 获取
- 在REF表单中编辑 `leader_name` 是不合理的

**建议**：
- ❌ **删除此字段** - REF级别不应该有负责人字段
- ✅ 负责人信息应该从关联的 `ProjectHeader` 获取
- 如果需要显示，使用只读显示：`{{ ref.header.leader_name }}`

---

#### 3. `expected_delivery_date` 字段 (第128-131行)
```html
<input type="date" name="expected_delivery_date" class="form-control" max="2050-12-31" required
       value="{{ ref.expected_delivery_date.strftime('%Y-%m-%d') if ref and ref.expected_delivery_date and not is_create else '' }}">
```

**问题**：
- ❌ `ProjectRef` 模型中**已删除**此字段（之前的重构）
- ⚠️ 模板中仍然存在并使用此字段
- ❌ 路由代码中也没有处理此字段（第1127行有注释但没有实际处理）

**影响**：
- 表单提交后，此字段的值会被忽略
- 可能导致用户困惑（填写了但没保存）

**建议**：
- ❌ **删除此字段** - 模型中没有对应字段
- ✅ 如果需要日期信息，可以存储在 `extra_info` JSON 中

---

#### 4. `actual_delivery_date` 字段 (第136-139行)
```html
<input type="date" name="actual_delivery_date" class="form-control" max="2050-12-31"
       value="{{ ref.actual_delivery_date.strftime('%Y-%m-%d') if ref and ref.actual_delivery_date and not is_create else '' }}">
```

**问题**：
- ❌ `ProjectRef` 模型中**已删除**此字段（之前的重构）
- ⚠️ 模板中仍然存在并使用此字段
- ❌ 路由代码中也没有处理此字段

**影响**：
- 表单提交后，此字段的值会被忽略
- 可能导致用户困惑

**建议**：
- ❌ **删除此字段** - 模型中没有对应字段
- ✅ 如果需要日期信息，可以存储在 `extra_info` JSON 中

---

### ⚠️ 缺失的字段

#### 1. `description` 和 `detailed_description` 字段

**问题**：
- ❌ 模板中没有显式的 `description` 和 `detailed_description` 输入字段
- ⚠️ 路由代码中使用 `request.form.get('description')` 但模板没有此字段
- ⚠️ 路由代码中 `detailed_description` 也有同样问题

**当前处理**：
- 路由中使用了默认值：`request.form.get('description', '签证订单')`
- 这意味着用户无法自定义描述

**建议**：
- ✅ 添加 `description` 输入字段（或使用 `name` 字段的值）
- ✅ 添加 `detailed_description` 输入字段
- 或者将自动生成的 `name` 映射到 `description`

---

#### 2. `currency` 字段

**问题**：
- ❌ 模板中没有 `currency` 字段
- ✅ 模型中有 `currency` 字段（默认 'SGD'）
- ⚠️ 模板中硬编码显示 "SGD"（第61、76行）

**建议**：
- 可以添加货币选择字段
- 或者保持默认 SGD（如果业务中都是 SGD）

---

## 总结

### 需要删除的字段
1. ❌ `leader_name` - REF 级别不应该有负责人字段（应该在 HID 级别）
2. ❌ `expected_delivery_date` - 模型中没有此字段
3. ❌ `actual_delivery_date` - 模型中没有此字段

### 需要修改的字段
1. ⚠️ `name` - 应该改为 `description`，或确保路由正确处理 `name` 字段
2. ⚠️ 添加 `description` 和 `detailed_description` 字段，或明确映射关系

### 可以保留的字段
1. ✅ `selling_price`, `cost_price` - 正确
2. ✅ `supplier_id` - 正确
3. ✅ `status` - 正确
4. ✅ `remarks` - 正确
5. ✅ `country`, `visa_type`, `applicant_info` - 正确存储在 extra_info 中

---

## 建议的修改方案

1. **删除冗余字段**：删除 `leader_name`、`expected_delivery_date`、`actual_delivery_date`
2. **修正 name 字段**：确保 `name` 正确映射到 `description`
3. **添加描述字段**：如果需要用户自定义描述，添加 `description` 和 `detailed_description` 输入框
4. **更新路由代码**：确保路由正确处理后端字段映射

---

**优先级**：高
**影响范围**：用户无法正确保存某些字段数据
**建议执行时间**：尽快修复

