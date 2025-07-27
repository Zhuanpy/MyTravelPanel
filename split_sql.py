#!/usr/bin/env python3
"""
分割大型SQL文件为多个小文件，并过滤不兼容的语句
"""

import re
from pathlib import Path

def split_sql_file(input_file, output_dir):
    """分割SQL文件"""
    
    print(f"开始分割文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 过滤掉不兼容的MySQL语句
    filtered_content = ""
    lines = content.split('\n')
    skip_next = False
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # 跳过不兼容的语句
        if any(keyword in line_lower for keyword in [
            'create database',
            'use ',
            '/*!',
            '*/',
            'set names',
            'set character_set',
            'set collation'
        ]):
            continue
        
        # 跳过空行和注释行
        if not line.strip() or line.strip().startswith('--'):
            continue
            
        filtered_content += line + '\n'
    
    print(f"过滤后内容大小: {len(filtered_content)} 字符")
    
    # 分割SQL语句
    statements = []
    current_statement = ""
    in_string = False
    string_char = None
    
    for char in filtered_content:
        current_statement += char
        
        if char in ['"', "'"]:
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None
        
        elif char == ';' and not in_string:
            stmt = current_statement.strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current_statement = ""
    
    # 添加最后一个语句（如果没有分号结尾）
    if current_statement.strip():
        statements.append(current_statement.strip())
    
    print(f"找到 {len(statements)} 个有效SQL语句")
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 按类型分组语句
    create_statements = []
    insert_statements = []
    other_statements = []
    
    for stmt in statements:
        stmt_lower = stmt.lower().strip()
        if stmt_lower.startswith('create'):
            create_statements.append(stmt)
        elif stmt_lower.startswith('insert'):
            insert_statements.append(stmt)
        else:
            other_statements.append(stmt)
    
    # 保存分组后的文件
    files_created = []
    
    # 保存CREATE语句
    if create_statements:
        create_file = output_path / "01_create_tables.sql"
        with open(create_file, 'w', encoding='utf-8') as f:
            f.write("-- 创建表结构（已过滤MySQL特有语句）\n")
            f.write("-- 文件大小: " + str(len('\n'.join(create_statements))) + " 字符\n\n")
            f.write('\n'.join(create_statements))
        files_created.append(str(create_file))
        print(f"✓ 创建表结构文件: {create_file}")
    
    # 保存其他语句
    if other_statements:
        other_file = output_path / "02_other_statements.sql"
        with open(other_file, 'w', encoding='utf-8') as f:
            f.write("-- 其他SQL语句\n")
            f.write("-- 文件大小: " + str(len('\n'.join(other_statements))) + " 字符\n\n")
            f.write('\n'.join(other_statements))
        files_created.append(str(other_file))
        print(f"✓ 其他语句文件: {other_file}")
    
    # 分批保存INSERT语句
    batch_size = 50  # 每批50个INSERT语句
    for i in range(0, len(insert_statements), batch_size):
        batch = insert_statements[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        insert_file = output_path / f"03_insert_data_batch_{batch_num:02d}.sql"
        
        with open(insert_file, 'w', encoding='utf-8') as f:
            f.write(f"-- 插入数据批次 {batch_num}\n")
            f.write(f"-- 包含 {len(batch)} 个INSERT语句\n")
            f.write("-- 文件大小: " + str(len('\n'.join(batch))) + " 字符\n\n")
            f.write('\n'.join(batch))
        
        files_created.append(str(insert_file))
        print(f"✓ 数据插入文件 {batch_num}: {insert_file}")
    
    print(f"\n✅ 分割完成！共创建 {len(files_created)} 个文件")
    print(f"输出目录: {output_path}")
    
    return files_created

def main():
    """主函数"""
    input_file = r"E:\DATA\20250725\travelindustry_supabase_fixed.sql"
    output_dir = r"E:\DATA\20250725\sql_parts"
    
    if not Path(input_file).exists():
        print(f"错误: 输入文件 {input_file} 不存在")
        return
    
    try:
        files = split_sql_file(input_file, output_dir)
        print("\n执行顺序:")
        print("1. 先执行 01_create_tables.sql")
        print("2. 再执行 02_other_statements.sql")
        print("3. 最后按顺序执行 03_insert_data_batch_*.sql")
    except Exception as e:
        print(f"分割过程中发生错误: {e}")

if __name__ == "__main__":
    main() 