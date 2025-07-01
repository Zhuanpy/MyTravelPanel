#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试单选身份选择功能
验证签证文档管理器中的单选身份选择器是否正常工作
"""

import requests
import json

def test_single_identity_selector():
    """测试单选身份选择功能"""
    base_url = "http://localhost:5000"
    
    print("🔍 测试单选身份选择功能")
    print("=" * 50)
    
    # 1. 测试获取签证文档配置
    print("\n1. 测试获取签证文档配置...")
    visa_type = "中国签证"
    url = f"{base_url}/visa/basic/api/get_visa_documents/{visa_type}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                identities = data.get('data', {}).get('identities', [])
                print(f"   ✅ 成功获取 {len(identities)} 个身份")
                print("   身份列表:")
                for i, identity in enumerate(identities):
                    print(f"      {i+1}. {identity.get('identity_zh')} (ID: {identity.get('id')})")
            else:
                print(f"   ❌ 获取失败: {data.get('message')}")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 2. 测试签证文档管理器页面
    print("\n2. 测试签证文档管理器页面...")
    url = f"{base_url}/visa/basic/visa_type_document_manager"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("   ✅ 页面加载成功")
            content = response.text
            
            # 检查单选模式相关元素
            checks = [
                ("选择要配置的身份（单选模式）", "单选模式标题"),
                ("选择第一个", "选择第一个按钮"),
                ("清空", "清空按钮"),
                ("当前选中", "当前选中显示"),
                ("未选择身份", "未选择身份显示")
            ]
            
            for check_text, description in checks:
                if check_text in content:
                    print(f"   ✅ {description}已添加")
                else:
                    print(f"   ⚠️  {description}可能未正确添加")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n🎉 测试完成！")
    print("\n📝 单选模式功能说明:")
    print("1. 身份选择器现在采用单选模式")
    print("2. 点击身份按钮会隐藏其他身份，只显示当前选中的身份")
    print("3. '选择第一个'按钮会自动选择第一个身份")
    print("4. '清空'按钮会隐藏所有身份配置")
    print("5. 配置摘要会显示当前选中的身份名称")
    print("6. 一次只能配置一个身份，避免界面混乱")

if __name__ == "__main__":
    test_single_identity_selector() 