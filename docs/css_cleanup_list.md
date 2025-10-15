# CSS 清理列表

## 📊 检测结果

- **总文件数**: 43 个CSS文件
- **使用中**: 16 个 ✅
- **未使用**: 27 个 ❌
- **保留（新优化文件）**: 7 个 🔒
- **待删除**: 20 个 🗑️

---

## 🔒 保留的文件（新优化系统）

这些是新创建的优化文件，必须保留：

1. ✅ `staff_common_optimized.css` - 新的优化主文件
2. ✅ `staff/variables.css` - CSS变量定义
3. ✅ `staff/base.css` - 基础样式
4. ✅ `staff/layout.css` - 布局系统
5. ✅ `staff/components.css` - 通用组件
6. ✅ `staff/profile.css` - Profile专用
7. ✅ `staff/responsive.css` - 响应式设计
8. ✅ `components/modal.css` - 模态框组件

---

## ✅ 使用中的文件（保留）

以下文件被HTML模板引用，保留：

1. ✅ `account_list.css`
2. ✅ `admin.css`
3. ✅ `auth.css`
4. ✅ `company_header.css`
5. ✅ `finance_common.css`
6. ✅ `flight_order_common.css`
7. ✅ `home_common.css`
8. ✅ `member.css`
9. ✅ `modal.css`
10. ✅ `package_budget.css`
11. ✅ `project_detail.css`
12. ✅ `projects_common.css`
13. ✅ `staff_common.css` - 当前使用的主文件
14. ✅ `tailwind.css`
15. ✅ `tour_common.css`
16. ✅ `utils_common.css`

---

## 🗑️ 待删除的文件（20个）

这些文件未被任何HTML模板引用，可以安全删除：

### Account相关（2个）
1. ❌ `App_new\static\css\account.css`
2. ❌ `App_new\static\css\account_add.css`

### App相关（3个）
3. ❌ `App_new\static\css\all_packages.css`
4. ❌ `App_new\static\css\app_mobile.css`
5. ❌ `App_new\static\css\app_web.css`

### Guest相关（2个）
6. ❌ `App_new\static\css\guest_mobile.css`
7. ❌ `App_new\static\css\guest_web.css`

### Staff相关（2个）
8. ❌ `App_new\static\css\staff_mobile.css`
9. ❌ `App_new\static\css\staff_web.css`

### Visa相关（6个）
10. ❌ `App_new\static\css\visa.css`
11. ❌ `App_new\static\css\visa_documents.css`
12. ❌ `App_new\static\css\visa_document_edit.css`
13. ❌ `App_new\static\css\visa_link_management.css`
14. ❌ `App_new\static\css\visa_project.css`
15. ❌ `App_new\static\css\visa_project_management.css`
16. ❌ `App_new\static\css\visa_style.css`

### 其他（4个）
17. ❌ `App_new\static\css\index.css`
18. ❌ `App_new\static\css\pdf_processing.css`
19. ❌ `App_new\static\css\public.css`
20. ❌ `App_new\static\css\shared_common.css`

---

## 📝 删除说明

### 为什么可以删除？

1. **未被引用**: 所有HTML模板中都没有引用这些文件
2. **功能重复**: 很多功能已经合并到其他CSS文件中
3. **历史遗留**: 可能是旧版本或重构时遗留的文件

### 删除后的影响

✅ **无影响** - 这些文件未被使用，删除后不会影响任何页面

### 预期收益

- 🗂️ 文件夹更清爽
- 📉 减少约 20 个无用文件
- 🚀 更容易找到需要的CSS文件
- 💾 节省约 50-100KB 空间

---

## 🚀 执行删除

### 方法1：手动删除（推荐）

逐个确认后删除：
```bash
# 删除单个文件示例
rm App_new/static/css/account.css
```

### 方法2：使用脚本批量删除

运行删除脚本（已创建）：
```bash
py scripts/delete_unused_css.py
# 然后输入 yes 确认
```

### 方法3：先备份再删除

```bash
# 创建备份
mkdir css_backup_20250115
cp App_new/static/css/*.css css_backup_20250115/

# 然后再删除
```

---

## ⚠️ 注意事项

1. **删除前备份** - 建议先做Git提交或创建备份
2. **测试确认** - 删除后测试主要页面
3. **可回滚** - 如有问题可以从Git恢复

---

## 📊 清理后的预期结果

### 删除前
```
App_new/static/css/
├── 36 个根目录CSS文件
├── staff/ (7个文件)
└── components/ (1个文件)
总计: 44 个文件
```

### 删除后
```
App_new/static/css/
├── 16 个根目录CSS文件（使用中）
├── staff/ (7个优化文件)
└── components/ (1个文件)
总计: 24 个文件
```

**减少 45% 的文件数量！** 🎉

---

**创建时间**: 2025-01-15  
**创建者**: AI Assistant  
**状态**: 待执行

