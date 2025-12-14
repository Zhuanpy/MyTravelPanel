# 快速修复项目485收款分配问题

## 问题描述

项目485的REF收款状态：
- R351: 售价 1860.00, 状态 partial
- R352: 售价 250.00, 状态 partial, **未收款 178.50**
- R353: 售价 95.00, 状态 partial, **未收款 70.44**
- R354: 售价 400.00, 状态 paid

**问题**：总余额为0，但R352和R353仍显示未收款（黄色）。

## 原因

项目级别收款记录的分配信息（`extra_info.distribution`）没有正确分配给R352和R353。

## 解决方案

### 方法1：运行修复脚本（推荐）

```bash
python fix_project_485_payment.py
```

脚本会：
1. 检查所有REF的当前收款情况
2. 重新分配项目级别收款记录
3. 按未收款比例优先分配给未收款多的REF
4. 更新所有REF的payment_status
5. 验证修复结果

### 方法2：手动SQL修复（如果脚本无法运行）

#### 步骤1：查看当前分配情况

```sql
-- 查看项目级别收款记录
SELECT 
    id,
    receipt_number,
    amount,
    extra_info
FROM project_receipts
WHERE header_id = 485 
  AND ref_id IS NULL
  AND status = 'confirmed';
```

#### 步骤2：查看REF信息

```sql
SELECT 
    id,
    ref_number,
    selling_price,
    payment_status
FROM project_refs
WHERE header_id = 485
ORDER BY id;
```

#### 步骤3：手动更新分配（需要根据实际情况调整）

如果项目级别收款总额是 248.94（正好是178.50 + 70.44），需要将这些金额分配给R352和R353。

**注意**：需要根据实际的收款记录ID和金额来更新 `extra_info` 字段。

## 修复后的预期结果

修复后刷新页面应该看到：
- ✅ R351: 未收款 0.00 (绿色)
- ✅ R352: 未收款 0.00 (绿色)
- ✅ R353: 未收款 0.00 (绿色)
- ✅ R354: 未收款 0.00 (绿色)
- ✅ 总余额: 0.00

## 验证

修复后访问：
- http://127.0.0.1:5000/projects/detail/485

检查：
1. 所有REF的未收款金额是否为0
2. 是否显示绿色（而不是黄色）
3. 总余额是否为0

