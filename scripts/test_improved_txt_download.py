#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的TXT下载功能
"""

import requests
import os
import time

def test_improved_txt_download():
    """测试优化后的TXT下载功能"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试优化后的TXT下载功能 ===")
    
    try:
        # 1. 测试下载txt文件
        print("1. 测试下载txt文件...")
        response = requests.get(f"{base_url}/package_budget/2/download_txt")
        
        if response.status_code == 200:
            print("   ✓ 下载请求成功")
            
            # 保存文件到本地测试
            filename = f"test_improved_budget_{int(time.time())}.txt"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✓ 文件已保存为: {filename}")
            
            # 读取文件内容验证
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"   文件内容长度: {len(content)} 字符")
            
            # 检查优化后的内容
            improvements = [
                ("旅游配套预算单", "标题"),
                ("【基本信息】", "基本信息标题"),
                ("【项目明细】", "项目明细标题"),
                ("【价格汇总】", "价格汇总标题"),
                ("分类：", "分类信息"),
                ("成人价格：", "成人价格"),
                ("儿童价格：", "儿童价格"),
                ("小计：", "项目小计"),
                ("适用：", "适用人数"),
                ("[可选项目]", "可选项目标记"),
                ("成人费用：", "成人费用汇总"),
                ("儿童费用：", "儿童费用汇总"),
                ("【分类汇总】", "分类汇总"),
                ("【备注】", "备注标题")
            ]
            
            for check_text, description in improvements:
                if check_text in content:
                    print(f"   ✓ 包含{description}")
                else:
                    print(f"   ✗ 缺少{description}")
            
            # 检查格式改进
            if "=" * 60 in content:
                print("   ✓ 使用更长的分隔线")
            else:
                print("   ✗ 分隔线长度未改进")
                
            if "人" in content and "成人人数：" in content:
                print("   ✓ 人数显示更清晰")
            else:
                print("   ✗ 人数显示格式未改进")
            
            # 检查文件名改进
            content_disposition = response.headers.get('Content-Disposition', '')
            if '4D3N BANGKOK FREE & EASY' in content_disposition or 'budget_' in content_disposition:
                print("   ✓ 文件名包含套餐名称")
            else:
                print("   ✗ 文件名格式未改进")
            
            # 显示部分内容预览
            print("\n   内容预览:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:20]):
                print(f"   {i+1:2d}: {line}")
            if len(lines) > 20:
                print("   ...")
            
            # 清理测试文件
            os.remove(filename)
            print(f"   ✓ 测试文件已清理: {filename}")
            
        else:
            print(f"   ✗ 下载请求失败: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n✅ 优化后的TXT下载功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_improved_txt_download() 