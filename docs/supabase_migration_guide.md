# MySQL到Supabase数据迁移指南

## 概述
本指南将帮助你将MySQL数据库中的travelindustry项目数据迁移到Supabase的travelindustry项目中。

## 准备工作

### 1. 安装依赖
```bash
pip install pandas pymysql
```

### 2. 确认数据库连接
确保你的MySQL数据库配置正确：
- 主机：localhost
- 用户：root
- 密码：***REMOVED****
- 数据库：travelindustry

## 迁移步骤

### 步骤1：导出MySQL数据
运行迁移脚本：
```bash
python scripts/export_mysql_to_supabase.py
```

这将创建 `supabase_migration` 目录，包含：
- 表结构SQL文件
- 数据CSV文件
- Supabase兼容的SQL文件
- 迁移报告

### 步骤2：登录Supabase Dashboard
1. 访问 [https://supabase.com](https://supabase.com)
2. 登录你的账户
3. 进入 `travelindustry` 项目

### 步骤3：创建表结构
1. 在Supabase Dashboard中，点击左侧菜单的 **SQL Editor**
2. 点击 **New Query**
3. 复制并执行生成的SQL文件内容（`*_supabase.sql`）
4. 按顺序执行，确保外键依赖正确

### 步骤4：导入数据
方法一：使用Table Editor
1. 点击左侧菜单的 **Table Editor**
2. 选择要导入数据的表
3. 点击 **Import** 按钮
4. 选择对应的CSV文件
5. 确认列映射并导入

方法二：使用SQL导入
```sql
-- 示例：导入CSV数据
COPY table_name FROM 'path/to/your/file.csv' WITH (FORMAT csv, HEADER true);
```

## 常见问题解决

### 1. 数据类型不兼容
MySQL和PostgreSQL的数据类型有差异：
- `int(11)` → `integer`
- `varchar(255)` → `text`
- `datetime` → `timestamp`
- `text` → `text`

### 2. 字符编码问题
确保CSV文件使用UTF-8编码：
```python
df.to_csv('file.csv', index=False, encoding='utf-8')
```

### 3. 外键约束
在导入数据前，可能需要临时禁用外键约束：
```sql
-- 禁用外键约束
SET session_replication_role = replica;

-- 导入数据后重新启用
SET session_replication_role = DEFAULT;
```

### 4. 自增ID问题
如果表有自增ID，确保在导入时正确处理：
```sql
-- 重置序列
SELECT setval('table_name_id_seq', (SELECT MAX(id) FROM table_name));
```

## 验证迁移结果

### 1. 检查表结构
```sql
-- 查看所有表
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- 查看表结构
\d table_name
```

### 2. 检查数据完整性
```sql
-- 检查记录数
SELECT COUNT(*) FROM table_name;

-- 检查关键数据
SELECT * FROM table_name LIMIT 5;
```

### 3. 测试关系
```sql
-- 测试外键关系
SELECT * FROM table1 
JOIN table2 ON table1.id = table2.table1_id 
LIMIT 5;
```

## 迁移后配置

### 1. 设置Row Level Security (RLS)
```sql
-- 启用RLS
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- 创建策略
CREATE POLICY "Enable read access for all users" ON table_name
    FOR SELECT USING (true);
```

### 2. 配置API访问
1. 在 **Settings** → **API** 中获取API密钥
2. 配置你的应用程序使用新的数据库连接

### 3. 设置实时功能
```sql
-- 启用实时功能
ALTER PUBLICATION supabase_realtime ADD TABLE table_name;
```

## 备份建议

### 1. 迁移前备份
```bash
# 备份MySQL数据
mysqldump -u root -p travelindustry > backup_before_migration.sql
```

### 2. 迁移后备份
在Supabase中创建数据库备份：
1. 进入项目设置
2. 点击 **Backups**
3. 创建手动备份

## 性能优化

### 1. 批量导入
对于大量数据，使用批量导入：
```sql
-- 批量插入示例
INSERT INTO table_name (col1, col2) VALUES 
(value1, value2),
(value3, value4),
...;
```

### 2. 索引优化
```sql
-- 创建索引
CREATE INDEX idx_column_name ON table_name(column_name);

-- 分析表
ANALYZE table_name;
```

## 联系支持

如果在迁移过程中遇到问题：
1. 查看Supabase文档：[https://supabase.com/docs](https://supabase.com/docs)
2. 在Supabase社区寻求帮助
3. 联系Supabase技术支持

## 迁移检查清单

- [ ] 导出MySQL数据
- [ ] 创建Supabase项目
- [ ] 执行表结构SQL
- [ ] 导入数据
- [ ] 验证数据完整性
- [ ] 配置RLS策略
- [ ] 测试API连接
- [ ] 创建备份
- [ ] 更新应用程序配置 