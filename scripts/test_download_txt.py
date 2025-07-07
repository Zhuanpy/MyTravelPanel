#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试下载txt功能
"""

import requests
import os
import time

def test_download_txt():
    """测试下载txt功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试下载txt功能 ===")
    
    try:
        # 1. 访问预算单详情页面
        print("1. 访问预算单详情页面...")
        response = requests.get(f"{base_url}/package_budget/2")
        if response.status_code == 200:
            print("   ✓ 预算单详情页面访问成功")
            
            # 检查页面是否包含下载按钮
            content = response.text
            if '下载TXT' in content:
                print("   ✓ 下载TXT按钮显示正常")
            else:
                print("   ✗ 下载TXT按钮未显示")
                
        else:
            print(f"   ✗ 预算单详情页面访问失败: {response.status_code}")
            return
        
        # 2. 测试下载txt文件
        print("2. 测试下载txt文件...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt")
        
        if response.status_code == 200:
            print("   ✓ 下载请求成功")
            
            # 检查响应头
            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            
            if 'text/plain' in content_type:
                print("   ✓ 文件类型正确 (text/plain)")
            else:
                print(f"   ✗ 文件类型错误: {content_type}")
                
            if 'attachment' in content_disposition:
                print("   ✓ 文件设置为下载模式")
            else:
                print(f"   ✗ 文件下载设置错误: {content_disposition}")
            
            # 保存文件到本地测试
            filename = f"test_budget_{int(time.time())}.txt"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✓ 文件已保存为: {filename}")
            
            # 读取文件内容验证
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if '配套名称：' in content:
                print("   ✓ 文件包含配套名称")
            else:
                print("   ✗ 文件缺少配套名称")
                
            if '项目明细：' in content:
                print("   ✓ 文件包含项目明细")
            else:
                print("   ✗ 文件缺少项目明细")
                
            if '价格汇总：' in content:
                print("   ✓ 文件包含价格汇总")
            else:
                print("   ✗ 文件缺少价格汇总")
                
            # 清理测试文件
            os.remove(filename)
            print(f"   ✓ 测试文件已清理: {filename}")
            
        else:
            print(f"   ✗ 下载失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
            return
        
        print("\n✅ 下载txt功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_download_txt() 