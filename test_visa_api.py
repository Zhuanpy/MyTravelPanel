#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试签证类型API的脚本
"""

import requests
import json

def test_visa_types_api():
    """测试签证类型API"""
    
    # 测试URL - 使用一个示例国家ID
    test_country_id = 1  # 假设国家ID为1
    
    url = f"http://127.0.0.1:5000/projects/ref/api/get_visa_types/{test_country_id}"
    
    print(f"测试API: {url}")
    
    try:
        response = requests.get(url)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('success'):
                visa_types = data.get('visa_types', [])
                print(f"找到 {len(visa_types)} 个签证类型:")
                for vt in visa_types:
                    print(f"  - {vt.get('visa_type')} (国家ID: {vt.get('country_id')})")
            else:
                print(f"API返回错误: {data.get('message')}")
        else:
            print(f"HTTP错误: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("连接错误: 无法连接到服务器，请确保Flask应用正在运行")
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"原始响应: {response.text}")

def test_countries_data():
    """测试国家数据"""
    print("\n" + "="*50)
    print("测试国家数据")
    print("="*50)
    
    # 这里可以添加测试国家数据的逻辑
    print("请检查数据库中是否有国家数据")
    print("可以使用以下SQL查询:")
    print("SELECT * FROM visa_countries LIMIT 5;")

if __name__ == "__main__":
    print("签证类型API测试")
    print("="*50)
    
    test_visa_types_api()
    test_countries_data()
    
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)
