# 项目收款状态问题分析

## 问题描述

项目485：
- ✅ 总余额为0（总收款 ≥ 总销售）
- ❌ 部分REF还显示黄色（部分收款/未收款）

## 问题原因分析

### 1. 数据不一致的根本原因

**REF的未收款金额计算** (`ref.unpaid_amount`):
```python
# 使用 ProjectReceipt.get_ref_total_received() 计算
# 包括：
# 1. 直接关联到REF的收款记录
# 2. 项目级别收款记录中分配给该REF的金额（从extra_info中解析）
total_received = ProjectReceipt.get_ref_total_received(ref.id, header_id)
unpaid = selling_price - total_received
```

**REF的付款状态字段** (`ref.payment_status`):
- 这是数据库中的一个枚举字段：'unpaid', 'partial', 'paid', 'refunded'
- 需要手动更新，不会自动计算

### 2. 可能的问题场景

#### 场景1：项目级别收款分配不完整
- 创建了项目级别的收款记录
- 但分配信息（`extra_info.distribution`）没有正确分配给所有REF
- 导致某些REF的 `unpaid_amount` > 0

#### 场景2：REF的payment_status未更新
- 收款记录已创建并分配
- 但REF的 `payment_status` 字段没有及时更新
- 导致显示状态与实际收款不符

#### 场景3：数据计算逻辑问题
- `ProjectReceipt.get_ref_total_received()` 计算正确
- 但项目总余额计算时可能使用了不同的逻辑
- 导致总余额为0但REF仍有未收款

### 3. 代码中的更新逻辑

**创建REF级别收款时** (`create_receipt`):
```python
total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')
if total_received >= ref.selling_price:
    ref.payment_status = 'paid'
elif total_received > 0:
    ref.payment_status = 'partial'
else:
    ref.payment_status = 'unpaid'
```
⚠️ **问题**：只计算了直接关联的收款，没有考虑项目级别分配

**创建项目级别收款时** (`create_header_receipt`):
```python
for ref in header.refs:
    if ref.selling_price:
        total_received = ProjectReceipt.get_ref_total_received(ref.id, header.id)
        if total_received >= ref.selling_price:
            ref.payment_status = 'paid'
        elif total_received > 0:
            ref.payment_status = 'partial'
        else:
            ref.payment_status = 'unpaid'
```
✅ **正确**：使用了 `get_ref_total_received()`，包括项目级别分配

## 解决方案

### 方案1：运行修复脚本（推荐）

执行 `fix_ref_payment_status.py` 脚本：
```bash
python fix_ref_payment_status.py
```

脚本会：
1. 检查所有REF的实际收款情况
2. 使用 `ProjectReceipt.get_ref_total_received()` 重新计算
3. 更新 `ref.payment_status` 字段
4. 显示详细的诊断信息

### 方案2：手动修复SQL

如果某些REF的未收款金额异常，可能是项目级别收款分配有问题：

```sql
-- 查看项目485的所有收款记录
SELECT 
    id,
    receipt_number,
    ref_id,
    header_id,
    amount,
    status,
    extra_info
FROM project_receipts
WHERE header_id = 485
ORDER BY id;

-- 查看项目485的所有REF
SELECT 
    id,
    ref_number,
    selling_price,
    payment_status
FROM project_refs
WHERE header_id = 485;
```

### 方案3：修复代码逻辑

在创建/更新REF级别收款时，也应该使用 `get_ref_total_received()`：

```python
# 修改 project_receipt.py 中的 create_receipt 函数
# 将：
total_received = sum(float(r.amount) for r in ref.receipts if r.status == 'confirmed')

# 改为：
total_received = ProjectReceipt.get_ref_total_received(ref.id, ref.header_id)
```

## 预防措施

1. **统一使用 `get_ref_total_received()`**：所有计算REF已收款的地方都应该使用这个方法
2. **及时更新payment_status**：每次创建/更新/删除收款记录后，都要更新相关REF的状态
3. **定期检查**：可以创建一个定时任务，定期检查并修复不一致的数据

## 检查清单

- [ ] 运行修复脚本检查项目485
- [ ] 检查项目级别收款记录的分配信息
- [ ] 验证所有REF的payment_status是否正确
- [ ] 检查是否有REF的未收款金额异常
- [ ] 修复代码中的逻辑问题（如果存在）

