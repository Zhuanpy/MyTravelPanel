#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试详情页面修复
"""

import requests
import time

def test_detail_page():
    """测试详情页面修复"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试详情页面修复 ===")
    
    try:
        # 1. 访问预算单列表
        print("1. 访问预算单列表...")
        response = requests.get(f"{base_url}/package_budget/list")
        if response.status_code == 200:
            print("   ✓ 预算单列表页面访问成功")
        else:
            print(f"   ✗ 预算单列表页面访问失败: {response.status_code}")
            return
        
        # 2. 访问预算单详情页面
        print("2. 访问预算单详情页面...")
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            print("   ✓ 预算单详情页面访问成功")
            
            # 检查页面内容
            content = response.text
            
            # 检查基本信息
            if '基本信息' in content:
                print("   ✓ 基本信息区域显示正常")
            else:
                print("   ✗ 基本信息区域未显示")
                
            # 检查下载按钮
            if '下载TXT' in content:
                print("   ✓ 下载TXT按钮显示正常")
            else:
                print("   ✗ 下载TXT按钮未显示")
                
            # 检查项目详细字段
            if '项目详细' in content:
                print("   ✓ 项目详细字段显示正常")
            else:
                print("   ✗ 项目详细字段未显示")
                
            # 检查项目类型字段是否已移除
            if '项目类型' not in content:
                print("   ✓ 项目类型字段已移除")
            else:
                print("   ✗ 项目类型字段仍然存在")
                
        else:
            print(f"   ✗ 预算单详情页面访问失败: {response.status_code}")
            print(f"   响应内容: {response.text[:500]}")
            return
        
        # 3. 测试下载功能
        print("3. 测试下载功能...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt")
        if response.status_code == 200:
            print("   ✓ 下载功能正常")
            
            # 检查文件内容
            content = response.text
            if '配套名称：' in content:
                print("   ✓ 下载文件包含配套名称")
            else:
                print("   ✗ 下载文件缺少配套名称")
                
            if '项目明细：' in content:
                print("   ✓ 下载文件包含项目明细")
            else:
                print("   ✗ 下载文件缺少项目明细")
                
        else:
            print(f"   ✗ 下载功能失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n✅ 详情页面修复测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_detail_page() 