#!/usr/bin/env python3
"""
测试删除资料功能的脚本
"""

import requests
import json

def test_delete_document():
    """测试删除资料功能"""
    
    # 测试参数
    base_url = "http://127.0.0.1:5000"
    document_id = 68  # 要删除的资料ID
    
    print(f"测试删除资料 ID: {document_id}")
    
    try:
        # 发送删除请求
        response = requests.post(
            f"{base_url}/visa/project/delete_document_status/{document_id}",
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('success'):
                print("✅ 删除成功!")
            else:
                print(f"❌ 删除失败: {data.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误: 无法连接到服务器")
    except requests.exceptions.Timeout:
        print("❌ 超时错误: 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求错误: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

def test_get_document_status():
    """测试获取资料状态"""
    
    base_url = "http://127.0.0.1:5000"
    project_id = 276  # 项目ID
    
    print(f"\n测试获取项目 {project_id} 的资料状态")
    
    try:
        response = requests.get(
            f"{base_url}/visa/project/get_document_status/{project_id}",
            headers={
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"项目资料状态: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 获取资料状态失败: {e}")

if __name__ == "__main__":
    test_get_document_status()
    test_delete_document() 