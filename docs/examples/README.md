# 共享脚本示例

这个目录用于存放对团队有价值的测试脚本和工具。

## 目录结构

```
docs/examples/
├── README.md                    # 本文件
├── shared_flight_test.py        # 航班功能测试脚本
├── shared_database_check.py     # 数据库检查脚本
├── shared_debug_tools.py        # 通用调试工具
└── templates/                   # 脚本模板
    ├── test_template.py         # 测试脚本模板
    └── debug_template.py        # 调试脚本模板
```

## 使用说明

### 1. 添加新的共享脚本

当 `scripts/` 目录中的某个脚本对团队有价值时：

1. 将文件复制到 `docs/examples/`
2. 重命名为 `shared_*.py`
3. 更新文档说明
4. 提交到Git

### 2. 使用共享脚本

```bash
# 复制到scripts目录使用
cp docs/examples/shared_flight_test.py scripts/
cd scripts
python shared_flight_test.py
```

### 3. 脚本模板

使用 `templates/` 目录中的模板快速创建新的测试脚本：

```bash
cp docs/examples/templates/test_template.py scripts/my_test.py
```

## 脚本列表

### shared_flight_test.py
- **功能**: 测试航班转换功能
- **用途**: 验证航班数据处理的正确性
- **使用方法**: 修改输入数据后运行

### shared_database_check.py
- **功能**: 检查数据库连接和表结构
- **用途**: 诊断数据库相关问题
- **使用方法**: 配置数据库连接后运行

### shared_debug_tools.py
- **功能**: 通用调试工具集合
- **用途**: 提供常用的调试功能
- **使用方法**: 导入需要的函数使用

## 注意事项

1. **不要包含敏感信息**: 确保脚本中不包含密码、密钥等敏感信息
2. **保持更新**: 定期更新脚本以适应项目变化
3. **文档完整**: 每个脚本都应该有详细的使用说明
4. **版本兼容**: 确保脚本与当前项目版本兼容

## 贡献指南

如果您有好的脚本想要分享：

1. 在 `scripts/` 中测试和完善
2. 确保代码质量和文档完整性
3. 提交到 `docs/examples/`
4. 更新本README文件 