#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试详情页面访问
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.PackageBudget import BudgetHeader

def test_detail_page():
    """测试详情页面访问"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找预算单
            budget = BudgetHeader.query.first()
            if not budget:
                print("❌ 没有找到预算单")
                return False
            
            print(f"📋 测试预算单 ID: {budget.id}")
            print(f"  套餐名称: {budget.package_name}")
            
            # 模拟访问详情页面
            with app.test_client() as client:
                print(f"\n🌐 访问详情页面: /package_budget/{budget.id}")
                
                response = client.get(f'/package_budget/{budget.id}')
                print(f"  状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print("  ✅ 页面访问成功")
                    print(f"  响应长度: {len(response.data)} 字节")
                elif response.status_code == 302:
                    print("  ⚠️  页面重定向")
                    print(f"  重定向到: {response.headers.get('Location', '未知')}")
                else:
                    print(f"  ❌ 页面访问失败")
                    print(f"  响应内容: {response.data.decode('utf-8', errors='ignore')[:500]}")
            
            # 测试列表页面
            print(f"\n🌐 访问列表页面: /package_budget/list")
            with app.test_client() as client:
                response = client.get('/package_budget/list')
                print(f"  状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print("  ✅ 列表页面访问成功")
                else:
                    print(f"  ❌ 列表页面访问失败")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    print("🚀 开始测试详情页面访问...")
    success = test_detail_page()
    if success:
        print("\n🎉 测试完成！")
    else:
        print("\n💥 测试失败！")
        sys.exit(1) 