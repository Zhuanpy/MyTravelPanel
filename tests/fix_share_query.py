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
    
    # 查找所有SHARE记录
    share_docs = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).all()
    
    print(f"\n找到 {len(share_docs)} 个SHARE记录:")
    print("=" * 60)
    
    for doc in share_docs:
        print(f"ID: {doc.id}")
        print(f"签证类型ID: {doc.visa_type_id}")
        print(f"身份ID: {doc.singapore_identity_id}")
        print(f"补充信息: {doc.additional_info}")
        
        # 检查关联的文档数量
        if hasattr(doc, 'selected_documents'):
            doc_count = len(doc.selected_documents) if doc.selected_documents else 0
            print(f"关联文档数量: {doc_count}")
            
            if doc_count > 0:
                print("关联的文档:")
                for selected_doc in doc.selected_documents:
                    print(f"  - {selected_doc.name} ({selected_doc.category})")
        else:
            print("没有selected_documents属性")
        
        print("-" * 40)
    
    # 优先选择id=9的记录
    target_share_doc = None
    for doc in share_docs:
        if doc.id == 9:
            target_share_doc = doc
            break
    
    if not target_share_doc and share_docs:
        target_share_doc = share_docs[0]  # 如果没有id=9，就用第一个
    
    if target_share_doc:
        print(f"\n推荐使用的SHARE记录ID: {target_share_doc.id}")
        print(f"该记录的关联文档数量: {len(target_share_doc.selected_documents) if target_share_doc.selected_documents else 0}")
    else:
        print("\n没有找到可用的SHARE记录") 