#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的下载功能
"""

import requests
import os
import time

def test_fixed_download():
    """测试修复后的下载功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试修复后的下载功能 ===")
    
    try:
        # 1. 测试下载txt文件
        print("1. 测试下载txt文件...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt", allow_redirects=False)
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✓ 下载请求成功")
            
            # 保存文件到本地测试
            filename = f"test_fixed_budget_{int(time.time())}.txt"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✓ 文件已保存为: {filename}")
            
            # 读取文件内容验证
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"   文件内容长度: {len(content)} 字符")
            
            # 检查关键内容
            if '旅游配套详情' in content:
                print("   ✓ 包含标题")
            else:
                print("   ✗ 缺少标题")
                
            if '【配套信息】' in content:
                print("   ✓ 包含配套信息")
            else:
                print("   ✗ 缺少配套信息")
                
            if '【包含项目】' in content:
                print("   ✓ 包含项目列表")
            else:
                print("   ✗ 缺少项目列表")
                
            if '【总价】' in content:
                print("   ✓ 包含总价")
            else:
                print("   ✗ 缺少总价")
            
            # 显示前10行内容
            print("\n   文件内容预览:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:10]):
                print(f"   {i+1:2d}: {line}")
            
            # 清理测试文件
            os.remove(filename)
            print(f"   ✓ 测试文件已清理: {filename}")
            
        elif response.status_code == 302:
            print("   ✗ 发生重定向，可能是错误处理")
            print(f"   重定向到: {response.headers.get('Location', 'Unknown')}")
        else:
            print(f"   ✗ 下载请求失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n✅ 修复后的下载功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_fixed_download() 