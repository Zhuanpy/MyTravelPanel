import requests
import json

# 检查SHARE记录的关联文档
response = requests.get('http://localhost:5000/visa/project/check_share_documents/日本签证')
data = response.json()

print("=== 日本签证SHARE记录检查结果 ===")
print(f"签证类型: {data.get('visa_type')}")
print(f"SHARE记录ID: {data.get('share_doc_id')}")
print(f"关联文档数量: {len(data.get('associated_documents', []))}")
print(f"消息: {data.get('message')}")

if data.get('associated_documents'):
    print("\n关联的文档:")
    for doc in data['associated_documents']:
        print(f"  - {doc['name']} ({doc['category']})")
else:
    print("\n没有关联的文档")

print(f"\n可用文档总数: {len(data.get('all_available_documents', []))}")
print("前5个可用文档:")
for doc in data.get('all_available_documents', [])[:5]:
    print(f"  - {doc['name']} ({doc['category']})") 