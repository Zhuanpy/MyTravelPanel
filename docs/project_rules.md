# MyTravelPanel 项目规则

## 测试文件管理规则

### 1. 测试文件存放位置
**所有测试文件必须放置在 `scripts/` 目录中**

- ✅ **正确**: `scripts/test_flight_conversion.py`
- ✅ **正确**: `scripts/debug_account_management.py`
- ✅ **正确**: `scripts/test_visa_api.py`
- ❌ **错误**: `App/tests/test_flight.py`
- ❌ **错误**: `test_something.py` (根目录)
- ❌ **错误**: `App/utils/test_cache.py`

### 2. 测试文件命名规范

#### 2.1 功能测试文件
- 格式: `test_<功能模块>_<具体功能>.py`
- 示例:
  - `test_flight_conversion.py`
  - `test_account_management.py`
  - `test_visa_api.py`
  - `test_package_budget.py`

#### 2.2 调试文件
- 格式: `debug_<问题描述>.py`
- 示例:
  - `debug_flight_500_error.py`
  - `debug_cache_issue.py`
  - `debug_database_connection.py`

#### 2.3 数据检查文件
- 格式: `check_<检查内容>.py`
- 示例:
  - `check_database_tables.py`
  - `check_flight_data.py`
  - `check_visa_types.py`

### 3. 测试文件内容规范

#### 3.1 文件头部注释
```python
"""
测试文件: test_flight_conversion.py
功能: 测试航班行程转换功能
作者: [开发者姓名]
创建时间: 2025-01-XX
最后修改: 2025-01-XX
"""

# 导入必要的模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.Flightmodels import FlightSchedule
# ... 其他导入
```

#### 3.2 测试函数命名
```python
def test_flight_conversion_basic():
    """测试基本的航班转换功能"""
    pass

def test_flight_conversion_with_luggage():
    """测试带行李信息的航班转换"""
    pass

def debug_flight_500_error():
    """调试航班转换500错误"""
    pass
```

### 4. 测试文件分类

#### 4.1 按功能模块分类
- **航班相关**: `test_flight_*.py`, `debug_flight_*.py`
- **签证相关**: `test_visa_*.py`, `debug_visa_*.py`
- **账号管理**: `test_account_*.py`, `debug_account_*.py`
- **配套预算**: `test_package_*.py`, `debug_package_*.py`

#### 4.2 按测试类型分类
- **单元测试**: `test_*.py`
- **集成测试**: `test_integration_*.py`
- **调试脚本**: `debug_*.py`
- **数据检查**: `check_*.py`
- **迁移脚本**: `migrate_*.py`

### 5. 执行测试文件

#### 5.1 在scripts目录中执行
```bash
cd scripts
python test_flight_conversion.py
```

#### 5.2 从项目根目录执行
```bash
python scripts/test_flight_conversion.py
```

### 6. 测试文件清理规则

#### 6.1 临时测试文件
- 临时创建的测试文件应该在测试完成后删除
- 如果测试文件包含重要信息，应该重命名为 `debug_*.py` 或 `check_*.py`

#### 6.2 长期保留的测试文件
- 功能测试文件: `test_*.py`
- 调试工具文件: `debug_*.py`
- 数据检查文件: `check_*.py`
- 迁移脚本: `migrate_*.py`

### 7. Git 版本控制

#### 7.1 scripts 文件夹被忽略
- `scripts/` 文件夹已添加到 `.gitignore` 中
- 测试文件不会被提交到Git仓库
- 这确保了仓库的整洁和安全性

#### 7.2 共享重要脚本
如果某个测试脚本对团队有价值：
1. 将文件复制到 `docs/examples/` 目录
2. 重命名为 `shared_*.py`
3. 手动添加到Git: `git add docs/examples/shared_*.py`

#### 7.3 使用脚本模板
- 测试脚本模板: `docs/examples/templates/test_template.py`
- 调试脚本模板: `docs/examples/templates/debug_template.py`

### 8. 违反规则的后果

- 测试文件放在错误位置将导致:
  - 代码审查不通过
  - 可能被意外提交到生产环境
  - 影响项目的整体结构

### 9. 最佳实践

1. **创建测试文件前先检查scripts目录**
2. **使用描述性的文件名**
3. **添加详细的文档注释**
4. **测试完成后及时清理临时文件**
5. **定期整理和归档测试文件**
6. **重要脚本及时共享到docs/examples**

---

**注意**: 此规则适用于所有项目成员，包括开发人员、测试人员和维护人员。 