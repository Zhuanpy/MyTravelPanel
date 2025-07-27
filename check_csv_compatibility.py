#!/usr/bin/env python3
"""
检查CSV文件与PostgreSQL表结构的兼容性
"""

import pandas as pd
import os
from pathlib import Path

def get_postgresql_schema():
    """获取PostgreSQL表结构定义"""
    schema = {
        'users': {
            'columns': ['id', 'username', 'email', 'password_hash', 'role', 'is_active', 
                       'created_at', 'last_login', 'full_name', 'phone', 'department', 'position'],
            'types': ['SERIAL', 'VARCHAR(80)', 'VARCHAR(120)', 'VARCHAR(128)', 'VARCHAR(20)', 
                     'BOOLEAN', 'TIMESTAMP', 'TIMESTAMP', 'VARCHAR(100)', 'VARCHAR(20)', 
                     'VARCHAR(100)', 'VARCHAR(100)']
        },
        'accounts': {
            'columns': ['id', 'platform', 'website_url', 'username', 'password', 'category', 
                       'owner', 'country', 'region', 'description', 'notes', 'file_materials', 
                       'additional_info', 'created_at', 'updated_at', 'click_count'],
            'types': ['SERIAL', 'VARCHAR(100)', 'VARCHAR(2000)', 'VARCHAR(100)', 'VARCHAR(100)', 
                     'VARCHAR(50)', 'VARCHAR(100)', 'VARCHAR(100)', 'VARCHAR(100)', 'TEXT', 
                     'TEXT', 'TEXT', 'TEXT', 'TIMESTAMP', 'TIMESTAMP', 'INTEGER']
        },
        'project_headers': {
            'columns': ['id', 'hid', 'desc', 'company_id', 'limit', 'contact', 'dept', 
                       'staff_id', 'staff_name', 'currency', 'leader_name', 'type', 'source', 
                       'country', 'status', 'created_at', 'updated_at', 'last_updated_by', 'remarks'],
            'types': ['SERIAL', 'VARCHAR(20)', 'VARCHAR(200)', 'INTEGER', 'VARCHAR(50)', 
                     'VARCHAR(50)', 'VARCHAR(50)', 'INTEGER', 'VARCHAR(50)', 'VARCHAR(10)', 
                     'VARCHAR(100)', 'VARCHAR(50)', 'VARCHAR(50)', 'VARCHAR(50)', 'VARCHAR(20)', 
                     'TIMESTAMP', 'TIMESTAMP', 'VARCHAR(50)', 'TEXT']
        },
        'project_refs': {
            'columns': ['id', 'ref_number', 'header_id', 'name', 'description', 'ref_type_id', 
                       'supplier_id', 'cost_price', 'selling_price', 'currency', 'status', 
                       'remarks', 'created_at', 'updated_at'],
            'types': ['SERIAL', 'VARCHAR(50)', 'INTEGER', 'VARCHAR(200)', 'TEXT', 'INTEGER', 
                     'INTEGER', 'NUMERIC(15,2)', 'NUMERIC(15,2)', 'VARCHAR(10)', 'VARCHAR(20)', 
                     'TEXT', 'TIMESTAMP', 'TIMESTAMP']
        },
        'visa_types': {
            'columns': ['id', 'visa_type', 'processing_time', 'fee', 'country_id'],
            'types': ['SERIAL', 'VARCHAR(50)', 'VARCHAR(200)', 'VARCHAR(200)', 'INTEGER']
        },
        'visa_countries': {
            'columns': ['id', 'country_name_CN', 'country_name_EN', 'country_code'],
            'types': ['SERIAL', 'VARCHAR(100)', 'VARCHAR(100)', 'VARCHAR(3)']
        },
        'flight_orders': {
            'columns': ['id', 'order_number', 'hid_number', 'project_header_id', 'project_ref_id', 
                       'passenger_name', 'contact_person', 'contact_phone', 'contact_name', 
                       'supplier_name', 'departure_date', 'itinerary', 'departure_city', 
                       'arrival_city', 'airline', 'flight_number', 'departure_time', 'arrival_time', 
                       'cabin_class', 'is_transit', 'transit_info', 'status', 'created_at', 'updated_at'],
            'types': ['SERIAL', 'VARCHAR(50)', 'VARCHAR(50)', 'INTEGER', 'INTEGER', 'VARCHAR(100)', 
                     'VARCHAR(100)', 'VARCHAR(20)', 'VARCHAR(50)', 'VARCHAR(100)', 'DATE', 
                     'VARCHAR(200)', 'VARCHAR(50)', 'VARCHAR(50)', 'VARCHAR(50)', 'VARCHAR(20)', 
                     'TIMESTAMP', 'TIMESTAMP', 'VARCHAR(20)', 'BOOLEAN', 'TEXT', 'VARCHAR(20)', 
                     'TIMESTAMP', 'TIMESTAMP']
        }
    }
    return schema

def check_csv_compatibility(csv_file, table_name):
    """检查单个CSV文件与表结构的兼容性"""
    
    schema = get_postgresql_schema()
    
    if table_name not in schema:
        print(f"⚠️  未找到表 {table_name} 的结构定义")
        return False
    
    table_schema = schema[table_name]
    expected_columns = table_schema['columns']
    expected_types = table_schema['types']
    
    print(f"\n🔍 检查表: {table_name}")
    print(f"CSV文件: {csv_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        csv_columns = list(df.columns)
        
        print(f"📊 CSV数据: {len(df)} 行, {len(csv_columns)} 列")
        print(f"📋 CSV列名: {csv_columns}")
        print(f"📋 期望列名: {expected_columns}")
        
        # 检查列数量
        if len(csv_columns) != len(expected_columns):
            print(f"❌ 列数量不匹配: CSV有{len(csv_columns)}列，期望{len(expected_columns)}列")
            return False
        
        # 检查列名
        column_mismatches = []
        for i, (csv_col, expected_col) in enumerate(zip(csv_columns, expected_columns)):
            if csv_col != expected_col:
                column_mismatches.append((csv_col, expected_col, i))
        
        if column_mismatches:
            print(f"❌ 列名不匹配:")
            for csv_col, expected_col, index in column_mismatches:
                print(f"   位置{index}: CSV='{csv_col}' vs 期望='{expected_col}'")
            return False
        
        # 检查数据类型
        print(f"✅ 列名匹配，检查数据类型...")
        
        data_type_issues = []
        for i, (col, expected_type) in enumerate(zip(csv_columns, expected_types)):
            sample_values = df[col].dropna().head(10)
            if len(sample_values) > 0:
                print(f"   列 {col} ({expected_type}): 样本值 = {list(sample_values)}")
                
                # 检查数值类型
                if 'NUMERIC' in expected_type or 'INTEGER' in expected_type or 'SERIAL' in expected_type:
                    non_numeric = []
                    for val in sample_values:
                        if val != '' and not str(val).replace('.', '').replace('-', '').isdigit():
                            non_numeric.append(val)
                    if non_numeric:
                        data_type_issues.append(f"列 {col}: 期望数值类型，但发现非数值: {non_numeric[:3]}")
        
        if data_type_issues:
            print(f"❌ 数据类型问题:")
            for issue in data_type_issues:
                print(f"   {issue}")
            return False
        
        print(f"✅ 兼容性检查通过！")
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_all_csv_files():
    """检查所有CSV文件"""
    
    csv_dir = r"E:\DATA\20250725\csv_exports"
    if not os.path.exists(csv_dir):
        print(f"❌ CSV目录不存在: {csv_dir}")
        return
    
    csv_files = list(Path(csv_dir).glob("*.csv"))
    
    if not csv_files:
        print(f"❌ 未找到CSV文件")
        return
    
    print(f"🔍 开始检查 {len(csv_files)} 个CSV文件...")
    
    compatible_files = []
    incompatible_files = []
    
    for csv_file in csv_files:
        table_name = csv_file.stem  # 去掉.csv扩展名
        
        if check_csv_compatibility(str(csv_file), table_name):
            compatible_files.append(csv_file)
        else:
            incompatible_files.append(csv_file)
    
    # 生成报告
    print(f"\n📊 检查结果:")
    print(f"✅ 兼容文件: {len(compatible_files)}")
    print(f"❌ 不兼容文件: {len(incompatible_files)}")
    
    if incompatible_files:
        print(f"\n❌ 不兼容的文件:")
        for file in incompatible_files:
            print(f"   - {file.name}")
    
    # 生成修复建议
    generate_fix_suggestions(incompatible_files)

def generate_fix_suggestions(incompatible_files):
    """生成修复建议"""
    
    if not incompatible_files:
        return
    
    suggestions = """
## 🔧 修复建议

### 1. 列名不匹配的解决方案
如果列名不匹配，可以：
- 重命名CSV文件的列名
- 在Supabase中修改表结构
- 使用列映射功能

### 2. 数据类型不匹配的解决方案
- 清理CSV中的非数值字符
- 统一日期格式
- 处理空值和特殊字符

### 3. 推荐修复步骤
1. 运行数据清理脚本
2. 重新导出CSV文件
3. 使用修复后的文件导入

### 4. 手动修复方法
对于特定文件，可以：
1. 打开CSV文件
2. 检查列名是否与表结构一致
3. 检查数据类型是否正确
4. 清理无效数据
"""
    
    print(suggestions)

if __name__ == "__main__":
    check_all_csv_files() 