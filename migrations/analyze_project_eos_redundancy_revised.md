# ProjectEO 表冗余字段分析报告（修正版）

## 业务逻辑
- **流程**：先创建 REF → 根据项目状态再生产 EO
- **关系**：EO 通过 `ref_id` 关联到 REF（一对一关系）
- **EO 性质**：EO 是**内部用于支付供应商的统计表单**，用于支付管理和统计

---

## 冗余字段分析（基于EO是统计表单）

既然EO是内部统计表单，用于支付供应商，那么：

### ✅ 应该删除的冗余字段：

1. **`name`** (EO订单名称)
   - REF已有：`description`, `detailed_description`
   - 可以通过 `eo.ref.description` 获取
   - **结论**：冗余，应删除

2. **`supplier_id`** (供应商ID)
   - REF已有：`supplier_id`
   - EO用于支付REF的供应商，应该使用同一个供应商
   - 可以通过 `eo.ref.supplier_id` 获取
   - **结论**：冗余，应删除

3. **`supplier_type`** (供应商类型)
   - REF已有：`ref_type_id` 关联到业务类型
   - 可以从 `eo.ref.ref_type` 获取
   - **结论**：冗余，应删除

4. **`currency`** (货币类型)
   - REF已有：`currency`
   - 支付应该使用REF的货币
   - 可以通过 `eo.ref.currency` 获取
   - **结论**：冗余，应删除

5. **`remarks`** (备注)
   - REF已有：`remarks`
   - 统计表单不需要单独的备注
   - 可以通过 `eo.ref.remarks` 获取
   - **结论**：冗余，应删除

### ✅ 应该保留的字段：

1. **`eo_number`** - EO编号（唯一标识）
2. **`ref_id`** - 关联到REF（外键）
3. **`amount`** - 支付金额（可能对应REF的cost_price，但可能有调整）
4. **`status`** - 支付状态（EO特有的状态）
5. **`external_system`**, **`external_status`**, **`external_reference`** - 外部系统信息（如果有用的话）

---

## 修改方案

### 需要删除的字段：
- `name`
- `supplier_id`
- `supplier_type`
- `currency`
- `remarks`

### 保留的字段：
- `id`
- `ref_id`
- `eo_number`
- `amount`
- `status`
- `external_system`
- `external_status`
- `external_reference`
- `created_at`
- `updated_at`

