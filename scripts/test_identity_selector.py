#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试身份选择功能
验证签证文档管理器中的身份选择器是否正常工作
"""

import requests
import json

def test_identity_selector():
    """测试身份选择功能"""
    base_url = "http://localhost:5000"
    
    print("🔍 测试身份选择功能")
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
                for identity in identities:
                    print(f"      - {identity.get('identity_zh')} (ID: {identity.get('id')})")
            else:
                print(f"   ❌ 获取失败: {data.get('message')}")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 2. 测试获取所有文档
    print("\n2. 测试获取所有文档...")
    url = f"{base_url}/visa/basic/api/get_all_documents"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                documents = data.get('documents', [])
                print(f"   ✅ 成功获取 {len(documents)} 个文档")
                
                # 按分类统计
                categories = {}
                for doc in documents:
                    category = doc.get('category', '其他')
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += 1
                
                print("   文档分类统计:")
                for category, count in categories.items():
                    print(f"      - {category}: {count} 个")
            else:
                print(f"   ❌ 获取失败: {data.get('message')}")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 3. 测试签证文档管理器页面
    print("\n3. 测试签证文档管理器页面...")
    url = f"{base_url}/visa/basic/visa_type_document_manager"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("   ✅ 页面加载成功")
            # 检查页面内容是否包含身份选择器
            content = response.text
            if "选择要配置的身份" in content:
                print("   ✅ 身份选择器已添加到页面")
            else:
                print("   ⚠️  身份选择器可能未正确添加")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n🎉 测试完成！")
    print("\n📝 使用说明:")
    print("1. 在签证文档管理器中，现在会显示身份选择区域")
    print("2. 点击身份按钮可以展开/收起对应的配置区域")
    print("3. 使用'全选'和'清空'按钮可以批量操作")
    print("4. 配置摘要会实时显示已展开的身份数量")

if __name__ == "__main__":
    test_identity_selector() 