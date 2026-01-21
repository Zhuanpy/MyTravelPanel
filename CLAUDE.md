# 项目规则

## 文件组织

- **脚本文件**: 放入 `scripts/` 目录
- **文档文件**: 放入 `docs/` 目录
- **模型文件**: 放入对应模块的 `models/` 目录
- **路由文件**: 放入对应模块的 `routes/` 目录
- **模板文件**: 放入 `templates/` 对应模块目录

## 代码风格

- **注释语言**: 中文
- **变量命名**: 英文，snake_case
- **类命名**: PascalCase
- **数据库字段**: 英文，snake_case

## 输出规范

- 面向客户的内容（发票、文档）使用**英文**
- 业务类型显示英文名称（Air Ticket, Hotel, Visa 等）
- 城市名使用英文（从 `city_name_en` 字段获取）

## 数据库操作

- 迁移脚本放入 `scripts/` 目录
- 注意事务管理（commit / rollback）
- 脚本运行方式: `python scripts/xxx.py`
- 脚本命名: `日期_脚本名称.py`

## 权限控制

- 需要登录的页面使用 `@login_required`
- 员工专用功能使用 `@staff_only`
- 管理员功能使用 `@admin_only`

## 注意事项

- 不要硬编码敏感信息（密码、API密钥）
- 模板中业务类型判断需同时检查 `code` 和中文 `name`

## Git 提交规则

- **不要自动推送**: 修改代码后等待用户验证，确认没问题后再推送到 GitHub
- 用户明确说"推送"或"push"时才执行 git push

## 临时文件管理

- Claude Code 临时文件 (`tmpclaude-*-cwd`) 已添加到 `.gitignore`，不会提交到 Git
- 如发现此类临时文件被误提交，使用 `rm -f tmpclaude-*-cwd` 删除后提交
- 临时文件应保持在项目根目录，由 `.gitignore` 自动忽略
