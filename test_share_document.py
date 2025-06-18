#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试共用文档功能
验证签证文档管理器中的共用文档功能是否正常工作
"""

import requests
import json

def test_share_document():
    """测试共用文档功能"""
    base_url = "http://localhost:5000"
    
    print("🔍 测试共用文档功能")
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
                documents = data.get('data', {}).get('documents', [])
                
                print(f"   ✅ 成功获取 {len(identities)} 个身份")
                print(f"   ✅ 成功获取 {len(documents)} 个文档配置")
                
                # 检查是否有共用文档配置
                share_docs = [doc for doc in documents if doc.get('singapore_identity_id') is None]
                print(f"   📋 共用文档配置数量: {len(share_docs)}")
                
                if share_docs:
                    print("   共用文档配置详情:")
                    for doc in share_docs:
                        selected_docs = doc.get('selected_documents', [])
                        print(f"     - 文档ID: {doc.get('id')}")
                        print(f"     - 选中文档数: {len(selected_docs)}")
                        print(f"     - 补充信息: {doc.get('additional_info', '无')}")
                else:
                    print("   ⚠️  未找到共用文档配置")
                
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
            
            # 检查共用文档相关元素
            checks = [
                ("共用文档", "共用文档选项"),
                ("fa-share-alt", "共用文档图标"),
                ("(共用)", "共用标识"),
                ("border-left: 4px solid var(--color-warning)", "共用文档样式"),
                ("选择第一个", "选择第一个按钮")
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
    
    # 3. 测试保存共用文档配置
    print("\n3. 测试保存共用文档配置...")
    test_data = {
        "identity_configs": [
            {
                "identity_id": None,  # 共用文档的identity_id为null
                "document_ids": [1, 2, 3],  # 示例文档ID
                "additional_info": "这是共用文档的补充信息"
            }
        ]
    }
    
    url = f"{base_url}/visa/basic/api/save_visa_documents/{visa_type}"
    
    try:
        response = requests.post(url, json=test_data)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ 共用文档配置保存成功")
            else:
                print(f"   ❌ 保存失败: {data.get('message')}")
        else:
            print(f"   ❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n🎉 测试完成！")
    print("\n📝 共用文档功能说明:")
    print("1. 共用文档选项现在显示在身份选择器的第一个位置")
    print("2. 共用文档有特殊的视觉标识（橙色边框和图标）")
    print("3. 共用文档的identity_id为null，区别于其他身份")
    print("4. '选择第一个'按钮会优先选择共用文档")
    print("5. 共用文档可以独立配置文档和补充信息")
    print("6. 保存时会正确处理共用文档的配置数据")

if __name__ == "__main__":
    test_share_document() 