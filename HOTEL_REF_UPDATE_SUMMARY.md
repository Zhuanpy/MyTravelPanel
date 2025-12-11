# 酒店REF创建页面更新总结

## 完成的功能

### 1. ✅ 添加Pax Name选择功能

参考 `create_other_ref.html`，在酒店ref创建页面中添加了：
- **Pax Name选择表格**：显示项目中的所有人员
- **全选功能**：可以一键全选所有人员
- **Leader设置**：可以为每个人员设置Leader
- **兼容性**：如果项目没有人员，显示手动输入框

### 2. ✅ 添加Departure字段

- **自动同步**：Departure字段自动使用Check In Date（入住日期）
- **只读**：Departure字段为只读，自动从Check In Date同步
- **提示信息**：显示"Departure使用Check In Date（入住日期），自动同步"

### 3. ✅ 数据保存到extra_info

所有新字段都保存到 `extra_info` JSON字段中：
- `pax_names`: 选中的人员ID列表
- `leader_id`: Leader人员ID
- `pax_name`: 手动输入的姓名（兼容模式）
- `departure_date`: 使用checkin_date的值
- `hotel_name`: 酒店名称
- `checkin_date`: 入住日期
- `checkout_date`: 退房日期
- `room_type`: 房型

## 修改的文件

### 1. 路由文件
**`App_new/business/projects/routes/project_ref.py`**

#### 创建路由 (`create_hotel_ref`)
- 添加获取项目人员列表（members）
- 传递 `header` 和 `members` 到模板

#### 提交路由 (`submit_hotel_ref`)
- 添加获取 `pax_names` 和 `leader_id` 的逻辑
- 构建 `extra_info` 对象，包含所有酒店专属字段
- 保存到 `ref.extra_info` JSON字段

#### 编辑路由 (`edit_hotel_ref`)
- 添加获取项目人员列表
- 解析 `extra_info` 并传递给模板
- 更新时也保存 `pax_names` 和 `leader_id`

### 2. 模板文件
**`App_new/templates/business/projects/project_ref/create_hotel_ref.html`**

#### 添加的功能
1. **Pax Name选择表格**（参考create_other_ref.html）
   - 显示所有项目人员
   - 支持多选
   - 支持设置Leader
   - 如果没有人员，显示手动输入框

2. **Departure字段**
   - 只读输入框
   - 自动从Check In Date同步

3. **JavaScript功能**
   - 全选Pax功能
   - Leader设置功能
   - Check In Date自动同步到Departure Date
   - 表单提交时收集pax_names和leader_id

4. **编辑模式支持**
   - 显示已有的数据（酒店名称、日期、价格等）
   - 显示已选中的人员
   - 显示已设置的Leader

## 使用说明

### 创建新的酒店REF

1. 访问 `/projects/ref/hotel/create/<header_id>`
2. 填写酒店名称、入住日期、退房日期等基本信息
3. **选择Pax Name**：
   - 如果有项目人员，从表格中选择
   - 可以勾选多个人员
   - 点击人员行的👤按钮设置Leader
4. **Departure字段**会自动从Check In Date同步
5. 填写价格、供应商等信息
6. 提交保存

### 编辑现有酒店REF

1. 访问编辑页面，所有已有数据会自动显示
2. 可以修改人员选择、Leader设置等
3. 修改Check In Date时，Departure会自动更新

## 数据结构

### extra_info JSON结构示例

```json
{
    "hotel_name": "Marina Bay Sands",
    "checkin_date": "2025-01-15",
    "checkout_date": "2025-01-18",
    "room_type": "Deluxe Room",
    "pax_names": [1, 2, 3],
    "leader_id": 1,
    "pax_name": "",
    "departure_date": "2025-01-15"
}
```

## 注意事项

1. **Pax Name选择**：
   - 如果项目中有人员，显示选择表格
   - 如果没有人员，显示手动输入框
   - 选择的人员ID存储在 `pax_names` 数组中

2. **Departure字段**：
   - 始终使用Check In Date的值
   - 字段为只读，不能手动修改
   - 会自动同步

3. **数据兼容性**：
   - 新创建的REF会有完整的extra_info
   - 旧REF如果没有extra_info，编辑时会自动创建
   - 支持手动输入的pax_name作为兼容模式

## 测试建议

1. **创建新REF**：
   - 测试有人员的情况
   - 测试没有人员的情况
   - 测试设置Leader功能
   - 测试Departure自动同步

2. **编辑现有REF**：
   - 测试显示已有数据
   - 测试修改人员选择
   - 测试修改日期时Departure同步

3. **数据保存**：
   - 检查extra_info是否正确保存
   - 检查pax_names数组是否正确
   - 检查leader_id是否正确

## 相关参考

- 参考模板：`create_other_ref.html`
- 数据模型：`ProjectMember`
- 数据存储：`ProjectRef.extra_info`




