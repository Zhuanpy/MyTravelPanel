from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
from App.exts import db

app = create_app()
with app.app_context():
    print('=== 测试身份选项获取 ===')
    
    # 获取第一个签证类型进行测试
    visa_type = VisaTypes.query.first()
    if not visa_type:
        print('没有找到签证类型')
        exit()
    
    print(f'测试签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
    
    # 模拟get_identity_options路由的逻辑
    decoded_visa_type = visa_type.visa_type
    print(f'签证类型: {decoded_visa_type}')
    
    # 从 VisaDocuments 表获取该签证类型实际已选择的身份
    selected_identities = db.session.query(VisaSingaporeIdentity.identity_zh)\
        .join(VisaDocuments, VisaDocuments.singapore_identity_id == VisaSingaporeIdentity.id)\
        .filter(VisaDocuments.visa_type_id == visa_type.id)\
        .filter(VisaDocuments.singapore_identity_id.isnot(None))\
        .distinct()\
        .all()
    
    # 将查询结果转换为列表
    identity_options = [identity[0] for identity in selected_identities]
    print(f'特定身份选项: {identity_options}')
    
    # 检查是否有SHARE记录
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    print(f'SHARE记录存在: {share_doc is not None}')
    if share_doc:
        print(f'SHARE记录ID: {share_doc.id}')
        print(f'SHARE记录文档数量: {len(share_doc.selected_documents)}')
    
    # 如果存在SHARE记录且SHARE不在已选择的身份列表中，则添加
    if share_doc and 'SHARE' not in identity_options:
        identity_options.append('SHARE')
    
    print(f'最终身份选项（包含SHARE）: {identity_options}')
    
    # 测试获取SHARE资料
    if 'SHARE' in identity_options:
        print('\n=== 测试SHARE资料获取 ===')


        # 模拟请求参数
        class MockRequest:
            def __init__(self):
                self.args = {}
        
        # 这里需要实际调用路由函数，但为了简化，我们直接测试数据获取逻辑
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=None
        ).first()
        
        if share_doc:
            documents = []
            if share_doc.selected_documents:
                for doc in share_doc.selected_documents:
                    documents.append({
                        'name': doc.name,
                        'type': 'document',
                        'category': '共用资料'
                    })
            
            print(f'SHARE资料数量: {len(documents)}')
            for doc in documents:
                print(f'  - {doc["name"]} ({doc["category"]})')
        else:
            print('未找到SHARE资料记录') 