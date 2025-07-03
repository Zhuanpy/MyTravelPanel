from App import create_app
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
from App.exts import db

app = create_app()
with app.app_context():
    print('=== 为澳大利亚签证创建SHARE记录 ===')
    
    # 获取澳大利亚签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='澳大利亚签证').first()
    if not visa_type:
        print('没有找到澳大利亚签证类型')
        exit()
    
    print(f'签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
    
    # 检查是否已存在SHARE记录
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    if share_doc:
        print(f'SHARE记录已存在 - ID: {share_doc.id}')
    else:
        print('创建新的SHARE记录...')
        share_doc = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=None,  # SHARE记录
            additional_info='澳大利亚签证共用资料补充信息'
        )
        db.session.add(share_doc)
        db.session.commit()
        print(f'SHARE记录创建成功 - ID: {share_doc.id}')
    
    # 添加常用共用文档
    common_documents = [
        '护照原件',
        '护照复印件',
        '近期护照照片',
        '身份证复印件',
        '出生证明',
        '学历证明',
        '工作证明',
        '银行对账单',
        '申请表',
        '签证申请表'
    ]
    
    print('\n添加共用文档...')
    added_count = 0
    for doc_name in common_documents:
        # 查找或创建文档
        doc = VisaDocumentsList.query.filter_by(name=doc_name).first()
        if not doc:
            doc = VisaDocumentsList(
                name=doc_name,
                category='共用资料'
            )
            db.session.add(doc)
            db.session.flush()
        
        # 添加到SHARE记录
        if doc not in share_doc.selected_documents:
            share_doc.selected_documents.append(doc)
            added_count += 1
            print(f'添加文档: {doc_name}')
    
    db.session.commit()
    print(f'\n成功添加 {added_count} 个共用文档')
    
    # 验证结果
    print(f'\n验证结果:')
    print(f'SHARE记录ID: {share_doc.id}')
    print(f'关联文档数量: {len(share_doc.selected_documents)}')
    for doc in share_doc.selected_documents:
        print(f'  - {doc.name}') 