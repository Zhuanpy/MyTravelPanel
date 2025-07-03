from App import create_app
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity

app = create_app()
with app.app_context():
    print('=== 测试SHARE数据状态 ===')
    
    # 获取第一个签证类型进行测试
    visa_type = VisaTypes.query.first()
    if not visa_type:
        print('没有找到签证类型')
        exit()
    
    print(f'测试签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
    
    # 检查SHARE记录
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    print(f'SHARE记录存在: {share_doc is not None}')
    if share_doc:
        print(f'SHARE记录ID: {share_doc.id}')
        print(f'SHARE记录selected_documents数量: {len(share_doc.selected_documents) if share_doc.selected_documents else 0}')
        if share_doc.selected_documents:
            print(f'SHARE记录文档列表: {[doc.name for doc in share_doc.selected_documents]}')
        else:
            print('SHARE记录没有关联的文档')
    else:
        print('SHARE记录不存在，需要创建')
    
    # 检查所有身份记录
    identities = VisaSingaporeIdentity.query.all()
    print(f'\n所有身份记录:')
    for identity in identities:
        print(f'- {identity.identity_zh} (ID: {identity.id})')
    
    # 检查该签证类型的所有文档记录
    all_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
    print(f'\n该签证类型的所有文档记录:')
    for doc in all_docs:
        identity_name = doc.singapore_identity.identity_zh if doc.singapore_identity else 'SHARE'
        doc_count = len(doc.selected_documents) if doc.selected_documents else 0
        print(f'- {identity_name} (ID: {doc.id}): {doc_count} 个文档')
        if doc.selected_documents:
            print(f'  文档列表: {[d.name for d in doc.selected_documents]}') 