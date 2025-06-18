import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity

app = create_app()

with app.app_context():
    print("=== 测试修复后的SHARE数据加载 ===")
    
    # 获取日本签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='日本签证').first()
    print(f"日本签证类型ID: {visa_type.id}")
    
    # 获取PR身份
    pr_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='PR').first()
    if pr_identity:
        print(f"PR身份ID: {pr_identity.id}")
        
        # 测试get_document_info方法
        print("\n调用get_document_info方法:")
        result = VisaDocuments.get_document_info(visa_type.id, pr_identity.id)
        
        print("\n返回结果:")
        print(f"文档信息: {result['document_info']}")
        print(f"补充信息: {result['additional_info']}")
        
        # 检查是否包含SHARE资料
        if "暂无共用资料" not in result['document_info']:
            print("\n✓ SHARE资料加载成功！")
        else:
            print("\n✗ SHARE资料仍然没有加载")
    else:
        print("没有找到PR身份记录") 