# 签证文档外键关联迁移文档

## 概述
将 `visa_documents_request` 表中的 `visa_type` 和 `singapore_identity` 字段从字符串改为外键关联，以提高数据一致性和查询性能。

## 修改内容

### 1. 模型修改 (App/models/Visamodels.py)
- 将 `visa_type` 字段改为 `visa_type_id` 外键
- 将 `singapore_identity` 字段改为 `singapore_identity_id` 外键
- 添加了与 `VisaTypes` 和 `VisaSingaporeIdentity` 的关系定义
- 更新了相关的类方法

### 2. 路由修改

#### App/routes/visa_documents.py
- 更新了 `manage_visas` 路由中的查询逻辑
- 修改了编辑和删除功能的数据处理
- 更新了查询构建方式，使用 JOIN 而不是字符串匹配

#### App/routes/visa_project.py
- 更新了 `visa_processing` 和 `visa_detail` 函数中的查询
- 修改了文档数据的获取和处理逻辑

#### App/routes/visa_basic_info.py
- 更新了签证类型创建时的文档关联逻辑
- 修改了身份选项的编辑和删除功能

### 3. 模板修改 (App/templates/visas/visa_document.html)
- 更新了数据显示方式，使用关系对象而不是字符串
- 修改了编辑模态框中的选择框，使用ID而不是名称
- 更新了按钮的 data 属性

### 4. 数据库迁移脚本 (scripts/update_visa_documents_foreign_keys.sql)
- 提供了完整的数据库迁移SQL脚本
- 包含数据转换、字段重命名和外键约束添加

## 执行步骤

### 1. 备份数据库
在执行迁移前，请务必备份数据库。

### 2. 执行数据库迁移
```sql
-- 执行 scripts/update_visa_documents_foreign_keys.sql 中的SQL语句
```

### 3. 重启应用
确保所有代码修改已部署，然后重启应用。

## 注意事项

1. **数据一致性**: 迁移前请确保所有 `visa_type` 和 `singapore_identity` 值在对应的表中都存在
2. **性能影响**: 外键关联可能会影响查询性能，但会提高数据一致性
3. **回滚计划**: 如果出现问题，可以回滚到使用字符串字段的版本

## 验证步骤

1. 检查签证资料管理页面是否正常显示
2. 测试编辑功能是否正常工作
3. 验证删除功能是否正常
4. 确认所有相关的查询都返回正确结果

## 兼容性

- 新代码需要新的数据库结构
- 旧代码无法与新数据库结构兼容
- 建议在测试环境中先验证所有功能 