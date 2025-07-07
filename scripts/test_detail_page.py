#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试详情页面
"""

import requests
import time

def test_detail_page():
    """测试详情页面"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试详情页面 ===")
    
    try:
        # 1. 访问预算单详情页面
        print("1. 访问预算单详情页面...")
        response = requests.get(f"{base_url}/package_budget/2")
        
        print(f"   状态码: {response.status_code}")
        print(f"   内容长度: {len(response.text)}")
        
        if response.status_code == 200:
            print("   ✓ 页面访问成功")
            
            # 检查页面内容
            content = response.text
            
            # 检查关键元素
            checks = [
                ("基本信息", "基本信息区域"),
                ("下载TXT", "下载按钮"),
                ("项目详细", "项目详细字段"),
                ("配套价格预算单详情", "页面标题"),
                ("明细项目", "明细项目区域"),
                ("添加项目", "添加项目按钮")
            ]
            
            for keyword, description in checks:
                if keyword in content:
                    print(f"   ✓ {description}存在")
                else:
                    print(f"   ✗ {description}不存在")
            
            # 检查是否有错误信息
            if "发生错误" in content:
                print("   ⚠️ 页面包含错误信息")
                # 提取错误信息
                import re
                error_match = re.search(r'发生错误[^<]*', content)
                if error_match:
                    print(f"   错误信息: {error_match.group()}")
            
            # 检查是否有异常信息
            if "Exception" in content or "Error" in content:
                print("   ⚠️ 页面包含异常信息")
            
        else:
            print(f"   ✗ 页面访问失败: {response.status_code}")
            print(f"   响应内容: {response.text[:500]}")
            return
        
        # 2. 测试下载功能
        print("\n2. 测试下载功能...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt")
        
        if response.status_code == 200:
            print("   ✓ 下载功能正常")
            
            # 检查下载内容
            content = response.text
            if '配套名称：' in content:
                print("   ✓ 下载文件包含配套名称")
            else:
                print("   ✗ 下载文件缺少配套名称")
                
            if '项目明细：' in content:
                print("   ✓ 下载文件包含项目明细")
            else:
                print("   ✗ 下载文件缺少项目明细")
                
            print(f"   下载文件长度: {len(content)} 字符")
            
        else:
            print(f"   ✗ 下载功能失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n✅ 详情页面测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_detail_page() 