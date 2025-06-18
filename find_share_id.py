import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes

app = create_app()

with app.app_context():
    # 获取日本签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='日本签证').first()
    if not visa_type:
        print("没有找到日本签证类型")
        exit(1)
    
    print(f"日本签证类型ID: {visa_type.id}")
    
    # 查找SHARE记录（singapore_identity_id为None）
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    if share_doc:
        print("=" * 50)
        print("SHARE记录详细信息:")
        print("=" * 50)
        print(f"记录ID: {share_doc.id}")
        print(f"签证类型ID: {share_doc.visa_type_id}")
        print(f"身份ID: {share_doc.singapore_identity_id}")
        print(f"补充信息: {share_doc.additional_info}")
        
        # 检查关联的文档数量
        if hasattr(share_doc, 'selected_documents'):
            doc_count = len(share_doc.selected_documents) if share_doc.selected_documents else 0
            print(f"关联文档数量: {doc_count}")
            
            if doc_count > 0:
                print("关联的文档:")
                for doc in share_doc.selected_documents:
                    print(f"  - {doc.name} ({doc.category})")
        else:
            print("没有selected_documents属性")
        
        print("=" * 50)
    else:
        print("没有找到SHARE记录") 