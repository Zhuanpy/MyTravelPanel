#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级Excel文件修复工具
处理严重损坏的Excel文件
"""

import os
import pandas as pd
import chardet
from pathlib import Path
import shutil
from datetime import datetime
import struct
import binascii

def analyze_file_header(file_path):
    """分析文件头部，判断文件类型"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            print(f"文件头部字节: {binascii.hexlify(header)}")
            
            # 检查Excel文件签名
            if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                return "Excel 97-2003 (.xls)"
            elif header.startswith(b'PK'):
                return "Excel 2007+ (.xlsx)"
            elif header.startswith(b'\x90>\xf3\xb1'):
                return "可能是损坏的Excel文件"
            else:
                return f"未知格式: {binascii.hexlify(header[:8])}"
    except Exception as e:
        return f"读取文件头部失败: {e}"

def try_binary_repair(file_path):
    """尝试二进制修复"""
    print("\n🔧 尝试二进制修复...")
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 查找Excel文件的标准头部
        excel_headers = [
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # Excel 97-2003
            b'PK\x03\x04',  # Excel 2007+
        ]
        
        for header in excel_headers:
            pos = data.find(header)
            if pos > 0:
                print(f"找到Excel头部在位置: {pos}")
                # 截取从头部开始的数据
                repaired_data = data[pos:]
                
                # 保存修复的数据
                repaired_path = Path(file_path).parent / f"{Path(file_path).stem}_binary_repaired{Path(file_path).suffix}"
                with open(repaired_path, 'wb') as f:
                    f.write(repaired_data)
                
                print(f"已保存二进制修复文件: {repaired_path}")
                return str(repaired_path)
        
        print("未找到有效的Excel文件头部")
        return None
        
    except Exception as e:
        print(f"二进制修复失败: {e}")
        return None

def try_hex_repair(file_path):
    """尝试十六进制修复"""
    print("\n🔧 尝试十六进制修复...")
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 查找可能的Excel文件结构
        # 查找常见的Excel标记
        markers = [
            b'Workbook',
            b'Worksheet',
            b'[Content_Types].xml',
            b'_rels/.rels',
            b'xl/workbook.xml'
        ]
        
        for marker in markers:
            pos = data.find(marker)
            if pos > 0:
                print(f"找到Excel标记 '{marker}' 在位置: {pos}")
                # 尝试从该位置开始修复
                repaired_data = data[pos-100:pos] + data[pos:]  # 包含一些前面的数据
                
                repaired_path = Path(file_path).parent / f"{Path(file_path).stem}_hex_repaired{Path(file_path).suffix}"
                with open(repaired_path, 'wb') as f:
                    f.write(repaired_data)
                
                print(f"已保存十六进制修复文件: {repaired_path}")
                return str(repaired_path)
        
        print("未找到Excel文件标记")
        return None
        
    except Exception as e:
        print(f"十六进制修复失败: {e}")
        return None

def try_text_extraction(file_path):
    """尝试提取文本内容"""
    print("\n🔧 尝试提取文本内容...")
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 尝试不同的编码提取文本
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252']
        extracted_text = []
        
        for encoding in encodings:
            try:
                text = data.decode(encoding, errors='ignore')
                # 提取可读的文本行
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 3]
                if lines:
                    extracted_text.extend([f"[{encoding}] {line}" for line in lines[:10]])  # 只取前10行
            except:
                continue
        
        if extracted_text:
            # 保存提取的文本
            text_path = Path(file_path).parent / f"{Path(file_path).stem}_extracted_text.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(extracted_text))
            
            print(f"已保存提取的文本: {text_path}")
            print("提取的文本内容:")
            for line in extracted_text[:5]:
                print(f"  {line}")
            
            return str(text_path)
        else:
            print("未能提取到可读文本")
            return None
            
    except Exception as e:
        print(f"文本提取失败: {e}")
        return None

def advanced_fix_excel():
    """高级Excel修复"""
    
    file_path = r"E:\Todays file\aaa\202208.xls"
    
    print("🔧 高级Excel文件修复工具")
    print("=" * 50)
    print(f"目标文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在 - {file_path}")
        return False
    
    # 创建备份
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = r"E:\Todays file\aaa\202208_advanced_backup_" + timestamp + ".xls"
    
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ 已创建备份文件: {backup_path}")
    except Exception as e:
        print(f"❌ 创建备份失败: {e}")
        return False
    
    # 分析文件头部
    file_type = analyze_file_header(file_path)
    print(f"📊 文件类型分析: {file_type}")
    
    # 尝试不同的修复方法
    repaired_files = []
    
    # 方法1: 二进制修复
    binary_repaired = try_binary_repair(file_path)
    if binary_repaired:
        repaired_files.append(binary_repaired)
    
    # 方法2: 十六进制修复
    hex_repaired = try_hex_repair(file_path)
    if hex_repaired:
        repaired_files.append(hex_repaired)
    
    # 方法3: 文本提取
    text_extracted = try_text_extraction(file_path)
    if text_extracted:
        repaired_files.append(text_extracted)
    
    # 尝试读取修复后的文件
    for repaired_file in repaired_files:
        print(f"\n🔍 尝试读取修复文件: {repaired_file}")
        
        try:
            # 尝试不同的读取方法
            df = None
            
            # 尝试Excel读取
            try:
                df = pd.read_excel(repaired_file)
                print(f"✅ 成功读取修复文件: {repaired_file}")
                print(f"📊 数据形状: {df.shape}")
                print(f"📝 列名: {list(df.columns)}")
                
                # 保存为Excel
                output_path = r"E:\Todays file\aaa\202208_advanced_fixed.xlsx"
                df.to_excel(output_path, index=False, engine='openpyxl')
                print(f"✅ 已保存修复后的Excel文件: {output_path}")
                
                # 显示数据预览
                print("\n📄 数据预览:")
                print(df.head())
                
                return True
                
            except Exception as e:
                print(f"❌ Excel读取失败: {e}")
            
            # 尝试CSV读取
            try:
                df = pd.read_csv(repaired_file, encoding='utf-8')
                print(f"✅ 成功读取为CSV: {repaired_file}")
                print(f"📊 数据形状: {df.shape}")
                
                # 保存为Excel
                output_path = r"E:\Todays file\aaa\202208_advanced_fixed.xlsx"
                df.to_excel(output_path, index=False, engine='openpyxl')
                print(f"✅ 已保存修复后的Excel文件: {output_path}")
                
                return True
                
            except Exception as e:
                print(f"❌ CSV读取失败: {e}")
                
        except Exception as e:
            print(f"❌ 处理修复文件失败: {e}")
    
    print("\n❌ 所有修复方法都失败了")
    print("💡 建议:")
    print("1. 检查原始文件是否完全损坏")
    print("2. 尝试从其他来源重新获取文件")
    print("3. 联系文件提供者获取正确的文件")
    
    return False

if __name__ == "__main__":
    success = advanced_fix_excel()
    
    if success:
        print("\n🎉 高级修复完成!")
        print("请检查生成的修复文件。")
    else:
        print("\n💥 高级修复失败!")
        print("文件可能已严重损坏，无法修复。") 