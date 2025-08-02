# Scripts 文件夹说明

## 📁 目录结构

```
scripts/
├── README.md                    # 本说明文件
├── database/                    # 数据库维护脚本
│   ├── create_auth_tables.sql
│   ├── fix_passwords_final.sql
│   └── ...
├── testing/                     # 测试脚本
│   ├── test_login.py
│   ├── test_auth_system.py
│   └── ...
├── data_update/                 # 数据更新脚本
│   ├── update_flight_ref_names_direct.py
│   └── ...
├── admin/                       # 管理脚本
│   ├── create_admin.py
│   ├── init_auth_system.py
│   └── ...
└── utils/                       # 工具脚本
    ├── debug_database_connection.py
    └── ...
```

## 🚀 快速开始

### 1. 数据库维护脚本
```bash
# 创建认证表
python scripts/database/create_auth_tables.sql

# 修复密码哈希
python scripts/database/fix_passwords_final.sql
```

### 2. 测试脚本
```bash
# 测试登录功能
python scripts/testing/test_login.py

# 测试认证系统
python scripts/testing/test_auth_system.py
```

### 3. 数据更新脚本
```bash
# 批量更新机票REF名称
python scripts/data_update/update_flight_ref_names_direct.py
```

### 4. 管理脚本
```bash
# 创建管理员账户
python scripts/admin/create_admin.py

# 初始化认证系统
python scripts/admin/init_auth_system.py
```

## 📋 脚本分类说明

### Database Scripts (数据库脚本)
- **用途**：数据库结构创建、数据修复、数据迁移
- **执行环境**：需要数据库连接权限
- **注意事项**：执行前请备份重要数据

### Testing Scripts (测试脚本)
- **用途**：功能测试、性能测试、调试
- **执行环境**：开发环境或测试环境
- **注意事项**：不要在生产环境执行

### Data Update Scripts (数据更新脚本)
- **用途**：批量数据更新、数据标准化
- **执行环境**：需要数据库写入权限
- **注意事项**：执行前请确认数据备份

### Admin Scripts (管理脚本)
- **用途**：系统管理、用户管理、权限管理
- **执行环境**：需要管理员权限
- **注意事项**：谨慎执行，影响系统配置

### Utils Scripts (工具脚本)
- **用途**：调试、诊断、辅助工具
- **执行环境**：开发环境
- **注意事项**：主要用于开发和调试

## ⚠️ 重要提醒

1. **执行前备份**：重要操作前请备份相关数据
2. **权限确认**：确保有足够的执行权限
3. **环境检查**：确认在正确的环境中执行
4. **日志记录**：重要操作请记录执行日志
5. **错误处理**：遇到错误请及时处理并记录

## 📞 联系方式

如有问题或建议，请联系项目维护者。

---

**最后更新：2024-01-XX** 