# CSS 合并快速迁移指南

## 🎯 目标

将所有使用 `visa_common.css` 的模板更新为使用统一的 `staff_common.css`。

## 📋 发现的文件

找到 **26 个文件**需要更新：

### Visa 模块（25 个文件）：
1. `visa_detail.html`
2. `visa_services.html`
3. `visa_services_country.html`
4. `manage_countries.html`
5. `visa_document.html`
6. `visa_documents_list.html`
7. `document_order_manager.html`
8. `edit_visa_type.html`
9. `visa_template_manager.html`
10. `visa_type_add.html`
11. `visa_type_detail.html`
12. `visa_type_edit.html`
13. `visa_type_edit_identities.html`
14. `visa_type_list.html`
15. `visa_type_management.html`
16. `签证类型.html`
17. `签证类型管理.html`
18. `manage_identities.html`
19. `visa_project_create.html`
20. `visa_project_detail.html`
21. `visa_project_edit.html`
22. `visa_project_list.html`
23. `debug_visit_stats.html`
24. `universal_visit_stats.html`
25. `visa_visit_stats.html`

### 其他模块（1 个文件）：
26. `todo_list.html`

## 🚀 快速更新方法

### 方法 1：使用 PowerShell 批量更新脚本 ⭐推荐

```powershell
# 在项目根目录执行
cd E:\MyProject\MyTravelWork\MyTravelPanel
.\scripts\batch_update_css.ps1
```

**流程**：
1. 脚本会列出所有需要更新的文件
2. 询问是否确认更新
3. 自动批量替换所有引用
4. 显示更新结果

### 方法 2：使用 Python 脚本

```bash
python scripts/update_css_references.py
```

### 方法 3：手动更新（不推荐）

在每个文件中查找并替换：

**查找**：
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/visa_common.css') }}">
```

**替换为**：
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/staff_common.css') }}">
```

### 方法 4：使用 VS Code 全局替换

1. 按 `Ctrl + Shift + H` 打开全局替换
2. 在"查找"框输入：`visa_common.css`
3. 在"替换"框输入：`staff_common.css`
4. 点击"在文件中替换"（Replace All）
5. 选择路径：`App_new/templates`

## ✅ 更新后检查清单

### 1. 文件更新验证
```powershell
# 检查是否还有引用 visa_common.css 的文件
Get-ChildItem -Path "App_new\templates" -Filter "*.html" -Recurse | Select-String -Pattern "visa_common.css"
```

应该返回：**无结果**

### 2. 功能测试

访问以下页面测试样式：

#### Visa 模块：
- [ ] http://127.0.0.1:5000/business/visa/
- [ ] 签证类型管理页面
- [ ] 签证项目详情页面
- [ ] 签证文档管理页面

#### Supplier 模块：
- [x] http://127.0.0.1:5000/supplier/
- [x] http://127.0.0.1:5000/supplier/<id>

#### 其他模块：
- [ ] Todo List 页面

### 3. 样式检查

每个页面应该：
- ✅ 卡片显示正常
- ✅ 按钮样式正确
- ✅ 表格格式正确
- ✅ 筛选栏布局正常
- ✅ 响应式设计正常

## 🔧 故障排除

### 问题 1：样式没有更新

**原因**：浏览器缓存

**解决**：
- 按 `Ctrl + F5` 强制刷新
- 或清除浏览器缓存

### 问题 2：样式显示异常

**检查**：
1. CSS 文件是否正确加载
2. 浏览器控制台是否有错误（F12）
3. 检查类名是否正确

**解决**：
- 确认引用路径：`css/staff_common.css`
- 确认类名使用了 `visa-*` 前缀

### 问题 3：部分样式缺失

**原因**：某些特殊样式可能在模板的 `<style>` 标签中

**解决**：
- 检查页面内联样式
- 确保没有冲突的 CSS

## 📊 更新统计

| 模块 | 文件数 | 状态 |
|------|--------|------|
| Visa 签证类型管理 | 8 | ⏳ 待更新 |
| Visa 签证文档管理 | 2 | ⏳ 待更新 |
| Visa 签证项目管理 | 4 | ⏳ 待更新 |
| Visa 签证国家管理 | 1 | ⏳ 待更新 |
| Visa 身份管理 | 1 | ⏳ 待更新 |
| Visa 其他 | 4 | ⏳ 待更新 |
| Visa 访问统计 | 4 | ⏳ 待更新 |
| Supplier 模块 | 2 | ✅ 已完成 |
| 工具模块 | 1 | ⏳ 待更新 |
| **总计** | **27** | **2/27** |

## 💡 建议的更新顺序

1. **立即更新**（已完成）：
   - ✅ Supplier 模块

2. **优先更新**：
   - Visa 项目管理页面（使用频率高）
   - Todo List 页面

3. **逐步更新**：
   - 其他 Visa 管理页面

4. **最后更新**：
   - 调试和统计页面

## 🚀 执行更新

### 推荐：使用批量更新脚本

```powershell
# 打开 PowerShell
cd E:\MyProject\MyTravelWork\MyTravelPanel

# 执行更新脚本
.\scripts\batch_update_css.ps1

# 按提示选择 "yes" 确认更新
```

### 或者：手动逐个更新

从最重要的页面开始，逐个测试和更新。

## 📝 更新后的操作

1. **提交到版本控制**：
   ```bash
   git add .
   git commit -m "合并 CSS：将 visa_common.css 整合到 staff_common.css"
   ```

2. **通知团队**：
   - 告知所有开发人员使用新的 CSS 文件
   - 分享本迁移指南

3. **文档更新**：
   - 更新开发文档
   - 更新组件使用说明

## ⚠️ 回滚方案

如果更新后出现问题，可以快速回滚：

```powershell
# 全局替换回去
Get-ChildItem -Path "App_new\templates" -Filter "*.html" -Recurse | ForEach-Object {
    (Get-Content $_.FullName -Raw -Encoding UTF8) `
        -replace "staff_common\.css", "visa_common.css" `
        | Set-Content $_.FullName -Encoding UTF8 -NoNewline
}
```

或使用 Git 回滚：
```bash
git checkout -- App_new/templates/
```

---

**创建日期**：2025-01-15  
**状态**：进行中  
**负责人**：开发团队

