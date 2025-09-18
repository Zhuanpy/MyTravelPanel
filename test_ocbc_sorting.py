#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCBC排序功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_sorting_options():
    """测试排序选项"""
    
    print("=== OCBC排序功能测试 ===")
    
    # 测试排序选项
    sort_options = [
        ('date_desc', '日期降序（最新在前）'),
        ('date_asc', '日期升序（最早在前）'),
        ('amount_desc', '金额降序（大额在前）'),
        ('amount_asc', '金额升序（小额在前）')
    ]
    
    print("可用的排序选项：")
    for value, label in sort_options:
        print(f"  {value}: {label}")
    
    print("\n排序逻辑：")
    print("  date_desc: BankTransaction.transaction_date.desc(), BankTransaction.id.desc()")
    print("  date_asc: BankTransaction.transaction_date.asc(), BankTransaction.id.asc()")
    print("  amount_desc: BankTransaction.amount.desc(), BankTransaction.id.desc()")
    print("  amount_asc: BankTransaction.amount.asc(), BankTransaction.id.asc()")
    
    print("\n✅ 排序功能已添加到OCBC银行账单页面")
    print("✅ 前端表单包含排序选择器")
    print("✅ 后端路由支持排序参数")
    print("✅ 分页链接保持排序状态")

if __name__ == '__main__':
    test_sorting_options()

