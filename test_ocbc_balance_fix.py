#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCBC余额列名修复
"""

import sys
from pathlib import Path
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_ocbc_column_mapping():
    """测试OCBC列名映射逻辑"""
    
    # 模拟OCBC数据列名
    test_columns = [
        'Statement Date',
        'Transaction Description', 
        'Debit Amount',
        'Credit Amount',
        'Closing Book Balance',  # 这是关键的余额列
        'Ref For Account Owner',
        'Our Ref'
    ]
    
    print("=== OCBC列名映射测试 ===")
    print(f"原始列名: {test_columns}")
    
    # 模拟_pick函数的逻辑
    def _pick(cols, candidates):
        for name in candidates:
            for c in cols:
                if name.lower() == str(c).lower():
                    return c
        for c in cols:
            s = str(c)
            for name in candidates:
                if name in s:
                    return c
        return None
    
    # 测试余额列映射
    bal_col = _pick(test_columns, ['Closing Book Balance', 'Ledger Balance', 'Available Balance', 'Balance', '余额'])
    
    print(f"选中的余额列: {bal_col}")
    
    if bal_col == 'Closing Book Balance':
        print("✅ 成功识别到 'Closing Book Balance' 列")
    else:
        print("❌ 未能识别到 'Closing Book Balance' 列")
    
    # 测试列名重命名
    rename_map = {}
    if bal_col: 
        rename_map[bal_col] = 'Balance'
    
    print(f"重命名映射: {rename_map}")
    
    # 测试DataFrame重命名
    df = pd.DataFrame(columns=test_columns)
    df.rename(columns=rename_map, inplace=True)
    
    print(f"重命名后的列名: {list(df.columns)}")
    
    if 'Balance' in df.columns:
        print("✅ 成功重命名为 'Balance' 列")
    else:
        print("❌ 重命名失败")

if __name__ == '__main__':
    test_ocbc_column_mapping()
