# Excel导入功能安装指南

## 依赖要求

Excel导入功能需要以下Python依赖库：

```bash
pip install pandas openpyxl
```

## 功能文件

### 前端文件
- `App/templates/company/list_companies.html` - 公司列表页面，包含Excel导入界面

### 后端文件
- `App/routes/company.py` - 公司管理路由，包含Excel导入和模板下载功能

### 测试文件
- `test_excel_import.py` - Excel导入功能测试脚本

### 文档文件
- `docs/excel_import_guide.md` - Excel导入功能使用指南

## 安装步骤

1. **安装依赖库**
   ```bash
   pip install pandas openpyxl
   ```

2. **验证安装**
   ```bash
   python test_excel_import.py
   ```

3. **启动应用**
   ```bash
   python app.py
   ```

4. **访问功能**
   - 打开浏览器访问公司管理页面
   - 点击"Excel导入"按钮测试功能

## 功能验证

### 1. 模板下载测试
- 点击"下载模板"按钮
- 检查下载的Excel文件格式是否正确

### 2. 数据导入测试
- 使用测试脚本生成的Excel文件
- 尝试导入数据并检查结果

### 3. 错误处理测试
- 尝试导入包含错误数据的文件
- 验证错误提示是否正确显示

## 注意事项

1. **文件权限**: 确保应用有读写文件的权限
2. **内存使用**: 大文件导入时注意内存使用情况
3. **数据库连接**: 确保数据库连接正常
4. **浏览器兼容性**: 建议使用现代浏览器（Chrome、Firefox、Safari、Edge）

## 故障排除

### 常见问题

1. **ImportError: No module named 'pandas'**
   - 解决方案: `pip install pandas`

2. **ImportError: No module named 'openpyxl'**
   - 解决方案: `pip install openpyxl`

3. **Excel文件无法读取**
   - 检查文件格式是否为.xlsx或.xls
   - 确保文件没有损坏

4. **导入失败**
   - 检查数据库连接
   - 查看应用日志获取详细错误信息

### 日志查看

如果遇到问题，可以查看应用日志：
```bash
tail -f logs/app.log
```

## 性能优化

1. **批量处理**: 大量数据导入时使用批量提交
2. **内存管理**: 及时释放不需要的数据
3. **错误恢复**: 支持部分成功的数据保存

## 安全考虑

1. **文件验证**: 验证上传文件的格式和大小
2. **数据验证**: 严格验证导入数据的格式
3. **权限控制**: 确保只有授权用户可以导入数据 