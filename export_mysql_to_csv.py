#!/usr/bin/env python3
"""
从MySQL导出数据为CSV格式，用于导入Supabase
"""

import pymysql
import pandas as pd
import os
from datetime import datetime
import json
import numpy as np

def get_mysql_connection():
    """获取MySQL连接"""
    return pymysql.connect(
        host='localhost',
        user='root',
        password='***REMOVED****',
        database='travelindustry',
        charset='utf8mb4'
    )

def get_table_list():
    """获取所有表名"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            return tables
    finally:
        conn.close()

def clean_data_for_postgresql(df):
    """清理数据以适配PostgreSQL"""
    
    for col in df.columns:
        if df[col].dtype == 'object':
            # 处理None值
            df[col] = df[col].replace(['None', 'NULL', 'null', ''], np.nan)
            
            # 处理特殊字符
            df[col] = df[col].astype(str).str.replace('\n', ' ').str.replace('\r', ' ')
            df[col] = df[col].str.replace('\\', '\\\\')  # 转义反斜杠
            
            # 将'nan'字符串转换为真正的NaN
            df[col] = df[col].replace('nan', np.nan)
    
    # 处理数值列
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    for col in numeric_columns:
        # 将NaN转换为空字符串，让PostgreSQL处理
        df[col] = df[col].replace([np.nan, None], '')
    
    return df

def get_table_schema(table_name):
    """获取表结构信息"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            return columns
    finally:
        conn.close()

def export_table_to_csv(table_name, output_dir):
    """导出单个表为CSV"""
    conn = get_mysql_connection()
    try:
        # 获取表结构
        schema = get_table_schema(table_name)
        print(f"📋 表 {table_name} 结构: {len(schema)} 列")
        
        # 读取数据
        query = f"SELECT * FROM `{table_name}`"
        df = pd.read_sql(query, conn)
        
        if df.empty:
            print(f"⚠️  表 {table_name} 为空，跳过导出")
            return None
        
        print(f"📊 原始数据: {len(df)} 行, {len(df.columns)} 列")
        
        # 清理数据
        df = clean_data_for_postgresql(df)
        
        # 保存为CSV
        output_file = os.path.join(output_dir, f"{table_name}.csv")
        df.to_csv(output_file, index=False, encoding='utf-8-sig', na_rep='')
        
        print(f"✅ 导出 {table_name}: {len(df)} 行 -> {output_file}")
        
        # 显示数据类型信息
        print(f"   数据类型: {dict(df.dtypes)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 导出表 {table_name} 失败: {e}")
        return None
    finally:
        conn.close()

def export_all_tables():
    """导出所有表"""
    output_dir = r"E:\DATA\20250725\csv_exports"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"开始导出MySQL数据到: {output_dir}")
    
    # 获取所有表
    tables = get_table_list()
    print(f"找到 {len(tables)} 个表")
    
    # 定义导出顺序（考虑外键依赖）
    export_order = [
        # 基础表（无依赖）
        'users',
        'accounts',
        'business_types',
        'suppliers',
        'supplier_data',
        'customer_companies',
        'customers',
        'visa_countries',
        'visa_singapore_identity',
        'visa_documents_list',
        'tasks',
        'todos',
        
        # 依赖表
        'project_headers',
        'project_refs',
        'project_eos',
        'visa_types',
        'visa_type_identities',
        'visa_documents_request',
        'visa_document_documents',
        'visa_type_links',
        'visa_projects',
        'visa_project_document_status',
        'airport_data',
        'flight_orders',
        'passengers',
        'flight_segments',
        'travelproducts',
        'tour_project',
        'tour_group',
        'package_budget_header',
        'package_budget_items',
    ]
    
    # 过滤存在的表
    existing_tables = [table for table in export_order if table in tables]
    missing_tables = [table for table in tables if table not in export_order]
    
    print(f"按顺序导出 {len(existing_tables)} 个表")
    if missing_tables:
        print(f"未定义顺序的表: {missing_tables}")
    
    exported_files = []
    
    # 按顺序导出
    for table in existing_tables:
        file_path = export_table_to_csv(table, output_dir)
        if file_path:
            exported_files.append(file_path)
    
    # 导出未定义顺序的表
    for table in missing_tables:
        file_path = export_table_to_csv(table, output_dir)
        if file_path:
            exported_files.append(file_path)
    
    # 生成导入指南
    generate_import_guide(exported_files, output_dir)
    
    print(f"\n✅ 导出完成！共导出 {len(exported_files)} 个文件")
    print(f"输出目录: {output_dir}")

def generate_import_guide(exported_files, output_dir):
    """生成导入指南"""
    guide_content = f"""# Supabase CSV 导入指南

## 导出信息
- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 导出文件数量: {len(exported_files)}

## 导入步骤

### 1. 在Supabase中创建表结构
首先在 Supabase SQL Editor 中执行 `postgresql_schema.sql` 文件创建所有表结构。

### 2. 按顺序导入CSV数据

**第一步：导入基础表（无外键依赖）**
"""
    
    # 基础表
    base_tables = ['users', 'accounts', 'business_types', 'suppliers', 'supplier_data', 
                   'customer_companies', 'customers', 'visa_countries', 'visa_singapore_identity', 
                   'visa_documents_list', 'tasks', 'todos']
    
    guide_content += "\n".join([f"- {table}.csv" for table in base_tables if f"{table}.csv" in [os.path.basename(f) for f in exported_files]])
    
    guide_content += """

**第二步：导入依赖表**
"""
    
    # 依赖表
    dependent_tables = ['project_headers', 'project_refs', 'project_eos', 'visa_types', 
                       'visa_type_identities', 'visa_documents_request', 'visa_document_documents',
                       'visa_type_links', 'visa_projects', 'visa_project_document_status',
                       'airport_data', 'flight_orders', 'passengers', 'flight_segments',
                       'travelproducts', 'tour_project', 'tour_group', 'package_budget_header',
                       'package_budget_items']
    
    guide_content += "\n".join([f"- {table}.csv" for table in dependent_tables if f"{table}.csv" in [os.path.basename(f) for f in exported_files]])
    
    guide_content += """

### 3. 导入方法

#### 方法1：使用Supabase Table Editor
1. 进入 Supabase Dashboard → Table Editor
2. 选择对应的表
3. 点击 "Import data" 按钮
4. 选择对应的CSV文件
5. 确认列映射后导入

#### 方法2：使用SQL COPY命令
```sql
-- 示例：导入users表
COPY users FROM '/path/to/users.csv' WITH (FORMAT csv, HEADER true);
```

### 4. 数据清理说明

本次导出的CSV文件已经过以下处理：
- 将 "None", "NULL", "null" 转换为空值
- 清理特殊字符（换行符、回车符）
- 转义反斜杠字符
- 数值列的空值处理

### 5. 注意事项

1. **编码问题**: CSV文件使用UTF-8编码
2. **数据类型**: 注意数字、日期等字段的数据类型匹配
3. **外键约束**: 确保先导入被引用的表，再导入引用表
4. **唯一约束**: 注意唯一字段的重复数据
5. **NULL值**: 空值已正确处理

### 6. 验证导入结果

导入完成后，可以运行以下SQL验证数据：

```sql
-- 检查各表的记录数
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'project_headers', COUNT(*) FROM project_headers
UNION ALL
SELECT 'visa_types', COUNT(*) FROM visa_types;
```

### 7. 导出文件列表
"""
    
    for file_path in exported_files:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        guide_content += f"- {file_name} ({file_size:,} bytes)\n"
    
    # 保存指南
    guide_file = os.path.join(output_dir, "import_guide.md")
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"📋 导入指南已生成: {guide_file}")

if __name__ == "__main__":
    export_all_tables() 