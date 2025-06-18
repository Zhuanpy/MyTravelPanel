import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, db

app = create_app()

with app.app_context():
    print("=== 调试SHARE数据加载问题 ===")
    
    # 1. 获取日本签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='日本签证').first()
    print(f"日本签证类型ID: {visa_type.id}")
    
    # 2. 查找所有SHARE记录（singapore_identity_id为None）
    share_docs = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).all()
    
    print(f"\n找到 {len(share_docs)} 个SHARE记录:")
    for doc in share_docs:
        print(f"  - ID: {doc.id}, 补充信息: {doc.additional_info}")
    
    # 3. 检查SHARE身份记录（从visa_singapore_identity表）
    share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
    if share_identity:
        print(f"\nSHARE身份记录: ID={share_identity.id}, 名称={share_identity.identity_zh}")
        
        # 4. 查找使用SHARE身份ID的记录
        share_docs_with_id = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        print(f"使用SHARE身份ID({share_identity.id})的记录:")
        for doc in share_docs_with_id:
            print(f"  - ID: {doc.id}, 补充信息: {doc.additional_info}")
            
            # 检查关联文档
            if hasattr(doc, 'selected_documents'):
                doc_count = len(doc.selected_documents) if doc.selected_documents else 0
                print(f"    关联文档数量: {doc_count}")
                if doc_count > 0:
                    for selected_doc in doc.selected_documents:
                        print(f"      - {selected_doc.name}")
    else:
        print("\n没有找到SHARE身份记录")
    
    # 5. 测试get_document_info方法
    print("\n=== 测试get_document_info方法 ===")
    
    # 测试PR身份
    pr_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='PR').first()
    if pr_identity:
        print(f"测试PR身份 (ID: {pr_identity.id}):")
        result = VisaDocuments.get_document_info(visa_type.id, pr_identity.id)
        print(f"返回结果: {result}")
    else:
        print("没有找到PR身份记录")
    
    # 6. 直接查询关联表
    print("\n=== 直接查询关联表 ===")
    
    # 查询所有日本签证相关的关联记录
    query = """
        SELECT vdd.visa_document_id, vdd.document_id, vdl.name, vdl.category
        FROM visa_document_documents vdd
        JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
        JOIN visa_documents_request vdr ON vdd.visa_document_id = vdr.id
        WHERE vdr.visa_type_id = :visa_type_id
        ORDER BY vdd.visa_document_id, vdl.name
    """
    
    result = db.session.execute(query, {'visa_type_id': visa_type.id}).fetchall()
    
    print("关联表数据:")
    current_doc_id = None
    for row in result:
        if row[0] != current_doc_id:
            current_doc_id = row[0]
            print(f"\n文档记录ID {row[0]}:")
        print(f"  - {row[2]} ({row[3]})") 