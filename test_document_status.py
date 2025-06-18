import requests
import json

def test_document_status_api():
    """测试资料状态更新API"""
    
    # 测试数据
    test_data = {
        'document_status_id': 1,  # 假设存在ID为1的记录
        'is_ready': True,
        'notes': '测试备注'
    }
    
    print("测试资料状态更新API...")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            'http://localhost:5000/visa/project/update_document_status',
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            json=test_data
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('success'):
                print("✅ API测试成功！")
            else:
                print(f"❌ API返回错误: {data.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_sync_documents_api():
    """测试同步资料清单API"""
    
    project_id = 276  # 使用您提到的项目ID
    
    print(f"\n测试同步资料清单API (项目ID: {project_id})...")
    
    try:
        response = requests.post(
            f'http://localhost:5000/visa/project/sync_project_documents/{project_id}',
            headers={
                'X-Requested-With': 'XMLHttpRequest'
            }
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('success'):
                print("✅ 同步API测试成功！")
            else:
                print(f"❌ 同步API返回错误: {data.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_document_status_api()
    test_sync_documents_api() 