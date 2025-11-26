# EO 表 amount 字段删除总结

## ✅ 完成状态：已完成

### 删除原因
用户确认：EO 的 `amount` 和 REF 的 `cost_price` 是一样的，且需要及时同步。
因此 `amount` 字段是冗余的，可以直接从关联的 REF 表获取。

### 修改内容

#### 1. **模型层** (`App_new/business/projects/models/eo.py`)
- ✅ 删除了 `amount` 字段定义
- ✅ 删除了 `sync_eo_prices_from_ref` 同步方法
- ✅ 添加了 `@property amount` 保持向后兼容（从 `ref.cost_price` 获取）
- ✅ 更新了 `formatted_amount` 属性使用 `ref.cost_price`

#### 2. **表单层** (`App_new/business/projects/forms/eo_forms.py`)
- ✅ 删除了 `amount` 字段的表单定义

#### 3. **路由层** (`App_new/business/projects/routes/project_eo.py`)
- ✅ 删除了创建 EO 时的 `amount` 赋值
- ✅ 删除了预填充 `amount` 的逻辑
- ✅ 更新了筛选条件：`ProjectEO.amount` → `ProjectRef.cost_price`
- ✅ 更新了排序逻辑：`ProjectEO.amount` → `ProjectRef.cost_price`
- ✅ 更新了 JSON 返回：`eo.amount` → `eo.ref.cost_price`

#### 4. **服务层** (`App_new/business/projects/services/project_stats.py`)
- ✅ 更新了统计逻辑：`eo.amount` → `eo.ref.cost_price`

#### 5. **路由层 - REF** (`App_new/business/projects/routes/project_ref.py`)
- ✅ 删除了所有 5 处调用 `sync_eo_prices_from_ref` 的地方
- ✅ 添加了注释说明：EO 金额现在直接从 REF 获取，无需同步

#### 6. **模板层**
- ✅ `eo_detail.html`: 更新使用 `eo.ref.cost_price`
- ✅ `eo_list.html`: 更新使用 `eo.ref.cost_price`

#### 7. **数据库迁移**
- ✅ 生成了 SQL 脚本：`migrations/update_project_eos_drop_amount.sql`

### 最终表结构

删除 `amount` 字段后，`project_eos` 表包含：
- `id` - 主键
- `ref_id` - 外键（关联到 project_refs）
- `eo_number` - EO编号
- `status` - 状态
- `external_system` - 外部系统名称
- `external_status` - 外部系统状态
- `external_reference` - 外部系统参考号
- `created_at` - 创建时间
- `updated_at` - 更新时间

**金额信息通过 `ref_id` 关联到 `project_refs.cost_price` 获取**

### 使用方式

#### 代码中使用金额
```python
# 方式1：直接通过关联获取
eo.ref.cost_price

# 方式2：通过属性获取（向后兼容）
eo.amount  # 返回 ref.cost_price

# 方式3：格式化显示
eo.formatted_amount  # 返回 "SGD 1,234.56" 格式
```

#### 查询和筛选
```python
# 筛选金额范围
ProjectRef.cost_price >= min_amount

# 排序
ProjectRef.cost_price

# 统计
sum([float(eo.ref.cost_price or 0) for eo in eos])
```

### 优势

1. **消除冗余**：不再需要存储重复的金额数据
2. **自动同步**：金额变化时，所有关联的 EO 自动反映最新金额
3. **数据一致性**：保证 EO 金额始终与 REF 成本价格一致
4. **简化维护**：不需要同步逻辑，减少代码复杂度

### 注意事项

- 查询 EO 时，确保关联查询 REF 表以获取金额信息
- 如果需要金额，必须通过 `eo.ref.cost_price` 获取
- 数据库中的 `amount` 字段需要执行 SQL 脚本删除

---
**修改完成时间**：2024年
**验证状态**：✅ 代码已全部更新，等待数据库迁移

