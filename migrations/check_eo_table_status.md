# EO 表状态检查

## 当前数据库表结构
根据您提供的信息，`project_eos` 表目前还有以下字段：

- ✅ `id` - 主键
- ✅ `ref_id` - 外键（保留）
- ✅ `eo_number` - EO编号（保留）
- ❌ `supplier_id` - **需要删除**（有外键约束，需先删除约束）
- ✅ `amount` - 金额（保留）
- ❌ `remarks` - **需要删除**
- ✅ `status` - 状态（保留）
- ✅ `created_at` - 创建时间（保留）
- ✅ `updated_at` - 更新时间（保留）
- ✅ `external_system` - 外部系统（保留）
- ✅ `external_status` - 外部状态（保留）
- ✅ `external_reference` - 外部参考号（保留）
- ❌ `currency` - **需要删除**

## 已删除的字段
- ✅ `name` - 已删除
- ✅ `supplier_type` - 已删除

## 代码修改状态

### ✅ 已完成
1. **模型文件** (`eo.py`) - 已删除冗余字段
2. **表单文件** (`eo_forms.py`) - 已删除冗余字段
3. **路由文件** (`project_eo.py`) - 已更新使用关联REF信息
4. **模板文件** - 正在清理中

### ⚠️ 需要执行
1. 执行SQL脚本删除数据库中的冗余字段
2. 清理模板文件中对已删除字段的引用

## 下一步操作

请按顺序执行以下SQL语句：

```sql
-- 1. 删除 supplier_id 的外键约束
ALTER TABLE `project_eos` 
DROP FOREIGN KEY `project_eos_ibfk_2`;

-- 2. 删除冗余字段
ALTER TABLE `project_eos` DROP COLUMN `supplier_id`;
ALTER TABLE `project_eos` DROP COLUMN `remarks`;
ALTER TABLE `project_eos` DROP COLUMN `currency`;
```

## 最终表结构

删除后，`project_eos` 表应只包含以下字段：
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

所有其他信息通过 `ref_id` 关联到 `project_refs` 表获取。

