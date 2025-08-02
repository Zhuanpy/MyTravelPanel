# 项目规则文档 (PROJECT RULES)

## 📁 项目结构规范

### 1. 脚本文件管理
- **所有脚本文件必须放在 `scripts/` 文件夹中**
- 禁止在根目录或其他目录中放置独立的脚本文件
- 脚本文件命名规范：`功能描述_版本.py`

### 2. 脚本文件分类

#### 2.1 数据库维护脚本
- 位置：`scripts/database/`
- 用途：数据库初始化、数据修复、数据迁移
- 示例：`create_auth_tables.sql`, `fix_passwords_final.sql`

#### 2.2 测试脚本
- 位置：`scripts/testing/`
- 用途：功能测试、性能测试、调试
- 示例：`test_login.py`, `test_auth_system.py`

#### 2.3 数据更新脚本
- 位置：`scripts/data_update/`
- 用途：批量数据更新、数据标准化
- 示例：`update_flight_ref_names_direct.py`

#### 2.4 管理脚本
- 位置：`scripts/admin/`
- 用途：系统管理、用户管理、权限管理
- 示例：`create_admin.py`, `init_auth_system.py`

### 3. 文件命名规范

#### 3.1 Python脚本
```
功能描述_版本.py
示例：
- update_flight_ref_names_direct.py
- test_login_direct.py
- create_admin.py
```

#### 3.2 SQL脚本
```
功能描述_版本.sql
示例：
- create_auth_tables.sql
- fix_passwords_final.sql
```

#### 3.3 文档文件
```
功能描述_版本.md
示例：
- manual_fix_guide.md
```

### 4. 脚本开发规范

#### 4.1 脚本头部注释
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：update_flight_ref_names_direct.py
功能描述：批量更新机票REF名称标准化
创建日期：2024-01-XX
作者：[作者名]
版本：1.0
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
from App.exts import db
```

#### 4.2 错误处理
```python
try:
    # 主要逻辑
    pass
except Exception as e:
    print(f"错误：{str(e)}")
    sys.exit(1)
```

#### 4.3 日志记录
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### 5. 脚本执行规范

#### 5.1 执行前检查
- 确认数据库连接正常
- 确认有足够的权限
- 备份重要数据

#### 5.2 执行方式
```bash
# 在项目根目录执行
python scripts/功能描述_版本.py

# 示例
python scripts/update_flight_ref_names_direct.py
```

### 6. 版本控制

#### 6.1 Git忽略规则
- 临时文件：`*.tmp`, `*.temp`
- 日志文件：`*.log`
- 缓存文件：`__pycache__/`, `*.pyc`

#### 6.2 提交规范
```
feat: 添加新功能脚本
fix: 修复脚本bug
docs: 更新脚本文档
refactor: 重构脚本代码
test: 添加测试脚本
```

### 7. 安全规范

#### 7.1 数据库操作
- 重要操作前必须备份数据
- 使用事务确保数据一致性
- 敏感操作需要确认提示

#### 7.2 权限控制
- 脚本执行需要适当的权限
- 避免硬编码敏感信息
- 使用环境变量管理配置

### 8. 文档维护

#### 8.1 脚本文档
每个脚本都应该包含：
- 功能描述
- 使用方法
- 参数说明
- 注意事项

#### 8.2 更新日志
记录脚本的修改历史：
- 版本号
- 修改日期
- 修改内容
- 影响范围

### 9. 质量保证

#### 9.1 代码审查
- 所有脚本提交前需要代码审查
- 确保代码符合项目规范
- 测试脚本功能正常

#### 9.2 测试要求
- 新脚本必须有对应的测试
- 重要脚本需要集成测试
- 定期运行测试脚本

### 10. 维护责任

#### 10.1 脚本维护
- 定期检查和更新脚本
- 删除过时的脚本
- 保持脚本文档的更新

#### 10.2 问题处理
- 及时修复脚本问题
- 记录问题和解决方案
- 分享最佳实践

---

## 📋 检查清单

### 创建新脚本时：
- [ ] 脚本放在正确的 `scripts/` 子目录中
- [ ] 文件名符合命名规范
- [ ] 包含完整的头部注释
- [ ] 有适当的错误处理
- [ ] 包含使用说明
- [ ] 测试脚本功能正常

### 提交脚本时：
- [ ] 代码符合项目规范
- [ ] 通过代码审查
- [ ] 更新相关文档
- [ ] 记录修改日志

### 维护脚本时：
- [ ] 定期检查脚本状态
- [ ] 更新过时的脚本
- [ ] 删除无用的脚本
- [ ] 保持文档同步

---

**最后更新：2024-01-XX**
**维护者：[维护者姓名]** 