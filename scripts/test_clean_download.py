#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试清理后的下载txt功能
"""

import requests
import os
import time

def test_clean_download():
    """测试清理后的下载txt功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试清理后的下载txt功能 ===")
    
    try:
        # 1. 测试下载txt文件
        print("1. 测试下载txt文件...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt")
        
        if response.status_code == 200:
            print("   ✓ 下载请求成功")
            
            # 保存文件到本地测试
            filename = f"test_clean_budget_{int(time.time())}.txt"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✓ 文件已保存为: {filename}")
            
            # 读取文件内容验证
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"   文件内容长度: {len(content)} 字符")
            
            # 检查清理后的内容
            if '配套名称：' in content:
                print("   ✓ 文件包含配套名称")
            else:
                print("   ✗ 文件缺少配套名称")
                
            if '项目明细：' in content:
                print("   ✓ 文件包含项目明细标题")
            else:
                print("   ✗ 文件缺少项目明细标题")
                
            if '总价：' in content:
                print("   ✓ 文件包含总价")
            else:
                print("   ✗ 文件缺少总价")
            
            # 检查是否移除了项目标题
            if '项目名称：' not in content:
                print("   ✓ 已移除'项目名称：'标题")
            else:
                print("   ✗ 仍然包含'项目名称：'标题")
                
            if '项目详细：' not in content:
                print("   ✓ 已移除'项目详细：'标题")
            else:
                print("   ✗ 仍然包含'项目详细：'标题")
            
            # 显示文件内容预览
            print("\n   文件内容预览:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:20]):  # 显示前20行
                print(f"   {i+1:2d}: {line}")
            if len(lines) > 20:
                print(f"   ... (还有 {len(lines)-20} 行)")
                
            # 清理测试文件
            os.remove(filename)
            print(f"   ✓ 测试文件已清理: {filename}")
            
        else:
            print(f"   ✗ 下载请求失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n✅ 清理下载功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_clean_download() 