from App import create_app
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity

app = create_app()
with app.app_context():
    print('=== 测试日本签证PR身份数据 ===')
    
    # 获取日本签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='日本签证').first()
    if not visa_type:
        print('没有找到日本签证类型')
        exit()
    
    print(f'签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
    
    # 获取PR身份记录
    pr_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='PR').first()
    if not pr_identity:
        print('没有找到PR身份记录')
        exit()
    
    print(f'PR身份: {pr_identity.identity_zh} (ID: {pr_identity.id})')
    
    # 检查SHARE记录
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    print(f'\n=== SHARE共用资料 ===')
    print(f'SHARE记录存在: {share_doc is not None}')
    if share_doc:
        print(f'SHARE记录ID: {share_doc.id}')
        print(f'SHARE记录selected_documents数量: {len(share_doc.selected_documents) if share_doc.selected_documents else 0}')
        if share_doc.selected_documents:
            print(f'SHARE记录文档列表:')
            for doc in share_doc.selected_documents:
                print(f'  - {doc.name} (ID: {doc.id})')
        else:
            print('SHARE记录没有关联的文档')
        print(f'SHARE补充信息: {share_doc.additional_info}')
    else:
        print('SHARE记录不存在')
    
    # 检查PR特定身份记录
    pr_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=pr_identity.id
    ).first()
    
    print(f'\n=== PR特定身份资料 ===')
    print(f'PR记录存在: {pr_doc is not None}')
    if pr_doc:
        print(f'PR记录ID: {pr_doc.id}')
        print(f'PR记录selected_documents数量: {len(pr_doc.selected_documents) if pr_doc.selected_documents else 0}')
        if pr_doc.selected_documents:
            print(f'PR记录文档列表:')
            for doc in pr_doc.selected_documents:
                print(f'  - {doc.name} (ID: {doc.id})')
        else:
            print('PR记录没有关联的文档')
        print(f'PR补充信息: {pr_doc.additional_info}')
    else:
        print('PR记录不存在')
    
    # 模拟前端API调用
    print(f'\n=== 模拟前端API调用结果 ===')
    
    # 使用VisaDocuments.get_document_info方法
    print(f'使用get_document_info方法获取PR完整资料:')
    pr_info = VisaDocuments.get_document_info(visa_type.id, pr_identity.id)
    print(f'文档信息: {pr_info["document_info"]}')
    print(f'补充信息: {pr_info["additional_info"]}')
    
    # 模拟get_project_documents API
    print(f'\n模拟get_project_documents API结果:')
    documents = []
    additional_info = []
    
    # 获取SHARE资料
    if share_doc and share_doc.selected_documents:
        for doc in share_doc.selected_documents:
            documents.append({
                'name': doc.name,
                'type': 'document',
                'category': '共用资料'
            })
    
    # 获取PR特定资料
    if pr_doc and pr_doc.selected_documents:
        for doc in pr_doc.selected_documents:
            documents.append({
                'name': doc.name,
                'type': 'document',
                'category': '特定身份资料'
            })
    
    # 获取补充信息
    if share_doc and share_doc.additional_info and share_doc.additional_info != '待输入':
        additional_info.append({
            'content': share_doc.additional_info,
            'type': 'additional',
            'category': '共用资料补充信息'
        })
    
    if pr_doc and pr_doc.additional_info and pr_doc.additional_info != 'None':
        additional_info.append({
            'content': pr_doc.additional_info,
            'type': 'additional',
            'category': '特定身份补充信息'
        })
    
    print(f'最终文档列表 ({len(documents)} 个):')
    for doc in documents:
        print(f'  - {doc["name"]} ({doc["category"]})')
    
    print(f'最终补充信息 ({len(additional_info)} 个):')
    for info in additional_info:
        print(f'  - {info["content"]} ({info["category"]})') 