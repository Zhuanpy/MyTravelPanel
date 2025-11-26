# 保险REF模板优化总结

## ✅ 已完成的优化

### 1. 模板优化

#### 1.1 表单结构
- ✅ 添加了表单 action，根据创建/编辑模式自动选择正确的路由
- ✅ 添加了 `header_id` 隐藏字段
- ✅ 添加了 `ref_id` 隐藏字段（编辑模式）
- ✅ 添加了 `detailed_description` 隐藏字段，支持自动生成

#### 1.2 字段映射
- ✅ `description` (保险名字) → `ref.description`
- ✅ `insurance_type` → `ref.extra_info['insurance_type']`
- ✅ `insured_person` (客人名字) → `ref.extra_info['insured_person']`
- ✅ `insurance_details` → `ref.extra_info['insurance_details']`
- ✅ `selling_price` → `ref.selling_price`
- ✅ `cost_price` → `ref.cost_price`
- ✅ `supplier_id` → `ref.supplier_id`
- ✅ `remarks` → `ref.remarks`

#### 1.3 JavaScript 优化
- ✅ 添加了自动生成 `detailed_description` 的逻辑
- ✅ 根据保险名字和保险类型自动生成详细描述
- ✅ 修正了 quickCreateEO 函数中的模板语法问题
- ✅ 修复了模板末尾的格式问题

#### 1.4 页面标题
- ✅ 统一了页面标题，创建和编辑模式显示不同标题

### 2. 路由代码优化

#### 2.1 `submit_insurance_ref` 路由
- ✅ 添加了 `extra_info` 的处理逻辑
- ✅ 将 `insurance_type`、`insured_person`、`insurance_details` 保存到 `extra_info` JSON
- ✅ 优化了 `description` 和 `detailed_description` 的处理逻辑
- ✅ 支持编辑和创建两种模式

#### 2.2 `edit_insurance_ref` 路由
- ✅ 添加了 `extra_info` 的处理逻辑（读取和保存）
- ✅ 解析 `insurance_info` 并传递到模板
- ✅ 修正了模板路径（使用 `create_insurance_ref.html`）
- ✅ 传递了 `header_id` 和 `insurance_info` 到模板

### 3. 数据流

#### 3.1 创建流程
1. 用户填写表单 → 提交到 `/insurance/submit`
2. 路由处理 → 创建 `ProjectRef` 实例
3. 将专属字段保存到 `extra_info` JSON
4. 保存到数据库

#### 3.2 编辑流程
1. 用户访问 `/insurance/edit/<ref_id>`
2. 路由读取 `ref.extra_info` → 解析为 `insurance_info`
3. 传递到模板，自动填充表单字段
4. 用户修改 → 提交到 `/insurance/edit/<ref_id>`
5. 路由更新 `ProjectRef` 和 `extra_info`
6. 保存到数据库

## 📋 字段清单

### ProjectRef 模型字段
- `description` - 保险名字
- `detailed_description` - 详细描述（自动生成）
- `selling_price` - 售价
- `cost_price` - 成本
- `supplier_id` - 供应商ID
- `remarks` - 备注
- `status` - 状态（默认为 'draft'）
- `payment_status` - 支付状态（默认为 'unpaid'）

### extra_info JSON 字段
- `insurance_type` - 保险类型（旅游保险、医疗保险等）
- `insured_person` - 客人名字
- `insurance_details` - 保险详情

## ⚠️ 注意事项

1. **extra_info 格式**：所有专属字段都存储在 `extra_info` JSON 中
2. **向后兼容**：编辑模式支持读取旧的 `insurance_company` 字段（已迁移到 `description`）
3. **自动生成**：`detailed_description` 根据 `description` 和 `insurance_type` 自动生成

---

**优化完成时间**：2024年
**状态**：✅ 所有优化已完成

