#!/usr/bin/env python3
"""
修复CSV文件以适配PostgreSQL导入
"""

import pandas as pd
import os
import numpy as np
from pathlib import Path

def fix_csv_for_postgresql(input_file, output_file):
    """修复CSV文件以适配PostgreSQL"""
    
    print(f"🔧 修复CSV文件: {input_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        print(f"📊 原始数据: {len(df)} 行, {len(df.columns)} 列")
        
        # 处理每一列
        for col in df.columns:
            print(f"   处理列: {col} (类型: {df[col].dtype})")
            
            if df[col].dtype == 'object':
                # 字符串列处理
                df[col] = df[col].astype(str)
                
                # 替换None值
                df[col] = df[col].replace(['None', 'NULL', 'null', 'nan', 'NaN'], '')
                
                # 清理特殊字符
                df[col] = df[col].str.replace('\n', ' ').str.replace('\r', ' ')
                df[col] = df[col].str.replace('\\', '\\\\')
                
                # 去除首尾空格
                df[col] = df[col].str.strip()
                
            elif pd.api.types.is_numeric_dtype(df[col]):
                # 数值列处理
                # 将NaN转换为空字符串
                df[col] = df[col].replace([np.nan, None], '')
                
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # 日期列处理
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                df[col] = df[col].replace(['NaT', 'nat'], '')
        
        # 保存修复后的文件
        df.to_csv(output_file, index=False, encoding='utf-8-sig', na_rep='')
        
        print(f"✅ 修复完成: {output_file}")
        print(f"   数据类型: {dict(df.dtypes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

def fix_all_csv_files():
    """修复所有CSV文件"""
    
    input_dir = r"E:\DATA\20250725\csv_exports"
    output_dir = r"E:\DATA\20250725\csv_exports_fixed"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"开始修复CSV文件...")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    
    # 获取所有CSV文件
    csv_files = list(Path(input_dir).glob("*.csv"))
    
    if not csv_files:
        print("❌ 未找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    fixed_files = []
    
    for csv_file in csv_files:
        output_file = os.path.join(output_dir, csv_file.name)
        
        if fix_csv_for_postgresql(str(csv_file), output_file):
            fixed_files.append(output_file)
    
    print(f"\n✅ 修复完成！共修复 {len(fixed_files)} 个文件")
    print(f"修复后的文件保存在: {output_dir}")
    
    # 生成修复报告
    generate_fix_report(fixed_files, output_dir)

def generate_fix_report(fixed_files, output_dir):
    """生成修复报告"""
    
    report_content = f"""# CSV文件修复报告

## 修复信息
- 修复时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
- 修复文件数量: {len(fixed_files)}

## 修复内容

### 数据清理
1. **None值处理**: 将 "None", "NULL", "null", "nan", "NaN" 转换为空字符串
2. **特殊字符清理**: 移除换行符、回车符，转义反斜杠
3. **数值列处理**: 将NaN值转换为空字符串
4. **日期格式**: 统一日期时间格式
5. **字符串清理**: 去除首尾空格

### 修复后的文件列表
"""
    
    for file_path in fixed_files:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        report_content += f"- {file_name} ({file_size:,} bytes)\n"
    
    report_content += """

## 导入建议

### 1. 使用修复后的文件
所有修复后的文件都在 `csv_exports_fixed` 目录中，请使用这些文件进行导入。

### 2. 导入顺序
按照以下顺序导入：

**基础表（无依赖）:**
- users.csv
- accounts.csv
- business_types.csv
- suppliers.csv
- supplier_data.csv
- customer_companies.csv
- customers.csv
- visa_countries.csv
- visa_singapore_identity.csv
- visa_documents_list.csv
- tasks.csv
- todos.csv

**依赖表:**
- project_headers.csv
- project_refs.csv
- project_eos.csv
- visa_types.csv
- visa_type_identities.csv
- visa_documents_request.csv
- visa_document_documents.csv
- visa_type_links.csv
- visa_projects.csv
- visa_project_document_status.csv
- airport_data.csv
- flight_orders.csv
- passengers.csv
- flight_segments.csv
- travelproducts.csv
- tour_project.csv
- tour_group.csv
- package_budget_header.csv
- package_budget_items.csv

### 3. 导入方法
1. 进入 Supabase Table Editor
2. 选择对应的表
3. 点击 "Import data"
4. 选择修复后的CSV文件
5. 确认列映射后导入

### 4. 验证导入
导入完成后运行以下SQL验证：

```sql
-- 检查记录数
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'project_headers', COUNT(*) FROM project_headers;
```
"""
    
    # 保存报告
    report_file = os.path.join(output_dir, "fix_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"📋 修复报告已生成: {report_file}")

if __name__ == "__main__":
    fix_all_csv_files() 