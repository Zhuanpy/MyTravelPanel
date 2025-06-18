from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
from App.exts import db
from urllib.parse import unquote
import html

app = create_app()
with app.app_context():
    print('=== 测试get_project_documents路由 ===')
    
    # 获取澳大利亚签证类型
    visa_type = VisaTypes.query.filter_by(visa_type='澳大利亚签证').first()
    if not visa_type:
        print('没有找到澳大利亚签证类型')
        exit()
    
    print(f'测试签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
    
    # 获取PR身份
    identity = VisaSingaporeIdentity.query.filter_by(identity_zh='PR').first()
    if not identity:
        print('没有找到PR身份记录')
        exit()
    
    print(f'测试身份: {identity.identity_zh} (ID: {identity.id})')
    
    # 模拟get_project_documents路由的逻辑
    decoded_visa_type = visa_type.visa_type
    decoded_identity = identity.identity_zh
    
    print(f'解码后的签证类型: {decoded_visa_type}')
    print(f'解码后的身份: {decoded_identity}')
    
    # 获取资料信息
    documents = []
    additional_info = []
    
    # 获取共用资料（SHARE）
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    print(f'SHARE记录存在: {share_doc is not None}')
    if share_doc:
        print(f'SHARE资料数量: {len(share_doc.selected_documents)}')
        if share_doc.selected_documents:
            for doc in share_doc.selected_documents:
                documents.append({
                    'name': doc.name,
                    'type': 'document',
                    'category': '共用资料'
                })
                print(f'  - {doc.name} (共用资料)')
    
    # 获取特定身份资料
    specific_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=identity.id
    ).first()
    
    print(f'特定身份记录存在: {specific_doc is not None}')
    if specific_doc:
        print(f'特定身份资料数量: {len(specific_doc.selected_documents)}')
        if specific_doc.selected_documents:
            for doc in specific_doc.selected_documents:
                documents.append({
                    'name': doc.name,
                    'type': 'document',
                    'category': '特定身份资料'
                })
                print(f'  - {doc.name} (特定身份资料)')
    
    # 获取补充信息
    if share_doc and share_doc.additional_info and share_doc.additional_info != '待输入':
        additional_info.append({
            'content': share_doc.additional_info,
            'type': 'additional',
            'category': '共用资料补充信息'
        })
        print(f'SHARE补充信息: {share_doc.additional_info}')
    
    if specific_doc and specific_doc.additional_info and specific_doc.additional_info != 'None':
        additional_info.append({
            'content': specific_doc.additional_info,
            'type': 'additional',
            'category': '特定身份补充信息'
        })
        print(f'特定身份补充信息: {specific_doc.additional_info}')
    
    print(f'\n最终结果:')
    print(f'资料总数: {len(documents)}')
    print(f'补充信息总数: {len(additional_info)}')
    
    # 模拟返回的JSON数据
    result = {
        'success': True,
        'documents': documents,
        'additional_info': additional_info
    }
    
    print(f'\n返回的JSON数据:')
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 测试URL编码
    import urllib.parse
    encoded_visa_type = urllib.parse.quote(decoded_visa_type)
    encoded_identity = urllib.parse.quote(decoded_identity)
    print(f'\nURL编码测试:')
    print(f'原始签证类型: {decoded_visa_type}')
    print(f'编码后签证类型: {encoded_visa_type}')
    print(f'原始身份: {decoded_identity}')
    print(f'编码后身份: {encoded_identity}')
    print(f'完整URL: /visa/project/get_project_documents/{encoded_visa_type}/{encoded_identity}') 