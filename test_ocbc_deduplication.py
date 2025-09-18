#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCBC去重逻辑修复
"""

import sys
from pathlib import Path
import hashlib

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_fingerprint_generation():
    """测试指纹生成逻辑"""
    
    # 模拟两条相似但不同的数据
    data1 = {
        't_date': '2025-08-28',
        'amt_raw': 166.8,
        'desc': 'xx-8908 Trip.com',
        'balance': 13077.2
    }
    
    data2 = {
        't_date': '2025-08-28',
        'amt_raw': 166.8,
        'desc': 'xx-8908 Trip.com',
        'balance': 12910.4
    }
    
    # 旧的指纹生成方式（不包含余额）
    old_fp1 = f"{data1['t_date']}|{data1['amt_raw']}|{data1['desc']}|OCBC"
    old_fp2 = f"{data2['t_date']}|{data2['amt_raw']}|{data2['desc']}|OCBC"
    old_hash1 = hashlib.sha1(old_fp1.encode('utf-8', errors='ignore')).hexdigest()
    old_hash2 = hashlib.sha1(old_fp2.encode('utf-8', errors='ignore')).hexdigest()
    
    # 新的指纹生成方式（包含余额）
    new_fp1 = f"{data1['t_date']}|{data1['amt_raw']}|{data1['desc']}|{data1['balance']}|OCBC"
    new_fp2 = f"{data2['t_date']}|{data2['amt_raw']}|{data2['desc']}|{data2['balance']}|OCBC"
    new_hash1 = hashlib.sha1(new_fp1.encode('utf-8', errors='ignore')).hexdigest()
    new_hash2 = hashlib.sha1(new_fp2.encode('utf-8', errors='ignore')).hexdigest()
    
    print("=== OCBC去重逻辑测试 ===")
    print(f"数据1: {data1}")
    print(f"数据2: {data2}")
    print()
    
    print("旧指纹生成方式（不包含余额）:")
    print(f"  数据1指纹: {old_hash1}")
    print(f"  数据2指纹: {old_hash2}")
    print(f"  是否重复: {'是' if old_hash1 == old_hash2 else '否'}")
    print()
    
    print("新指纹生成方式（包含余额）:")
    print(f"  数据1指纹: {new_hash1}")
    print(f"  数据2指纹: {new_hash2}")
    print(f"  是否重复: {'是' if new_hash1 == new_hash2 else '否'}")
    print()
    
    if old_hash1 == old_hash2 and new_hash1 != new_hash2:
        print("✅ 修复成功！新逻辑可以正确区分这两条数据")
    else:
        print("❌ 修复可能有问题")

if __name__ == '__main__':
    test_fingerprint_generation()

