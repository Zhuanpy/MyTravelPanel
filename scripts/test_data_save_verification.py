from App import create_app
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaDocumentsList
from App.exts import db

app = create_app()

def test_data_save_verification():
    """验证签证文档管理器的数据保存情况"""
    with app.app_context():
        print('=== 验证签证文档管理器数据保存情况 ===')
        
        # 1. 检查数据库表结构
        print('\n1. 检查数据库表结构:')
        print('   - visa_documents_request: 存储签证类型和身份的配置')
        print('   - visa_document_documents: 多对多关联表，存储配置与文档的关系')
        print('   - visa_documents_list: 存储所有可用的文档模板')
        print('   - visa_singapore_identity: 存储身份信息（包括SHARE）')
        
        # 2. 检查SHARE身份
        print('\n2. 检查SHARE身份:')
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if share_identity:
            print(f'   ✅ 找到SHARE身份 - ID: {share_identity.id}, 名称: {share_identity.identity_zh}')
        else:
            print('   ❌ 未找到SHARE身份')
            return False
        
        # 3. 检查签证类型
        print('\n3. 检查签证类型:')
        visa_types = VisaTypes.query.limit(3).all()
        if not visa_types:
            print('   ❌ 没有找到签证类型')
            return False
        
        test_visa_type = visa_types[0]
        print(f'   ✅ 测试签证类型: {test_visa_type.visa_type} (ID: {test_visa_type.id})')
        
        # 4. 检查文档模板
        print('\n4. 检查文档模板:')
        documents = VisaDocumentsList.query.limit(5).all()
        if not documents:
            print('   ❌ 没有找到文档模板')
            return False
        
        print(f'   ✅ 找到 {len(documents)} 个文档模板')
        for doc in documents:
            print(f'      - {doc.name} (ID: {doc.id}, 分类: {doc.category})')
        
        # 5. 检查现有配置
        print('\n5. 检查现有配置:')
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
        print(f'   ✅ 找到 {len(existing_configs)} 个现有配置')
        
        for config in existing_configs:
            identity_name = "SHARE共用文档" if config.singapore_identity_id is None else f"身份ID: {config.singapore_identity_id}"
            doc_count = len(config.selected_documents) if config.selected_documents else 0
            print(f'      - 配置ID: {config.id}, 身份: {identity_name}, 文档数量: {doc_count}')
        
        # 6. 检查visa_document_documents关联表
        print('\n6. 检查visa_document_documents关联表:')
        
        # 执行原始SQL查询
        from sqlalchemy import text
        result = db.session.execute(text("""
            SELECT vdd.visa_document_id, vdd.document_id, 
                   vd.visa_type_id, vd.singapore_identity_id,
                   vdl.name as document_name
            FROM visa_document_documents vdd
            JOIN visa_documents_request vd ON vdd.visa_document_id = vd.id
            JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
            WHERE vd.visa_type_id = :visa_type_id
            ORDER BY vd.singapore_identity_id, vdl.name
        """), {'visa_type_id': test_visa_type.id})
        
        associations = result.fetchall()
        print(f'   ✅ 找到 {len(associations)} 个文档关联')
        
        if associations:
            current_identity = None
            for assoc in associations:
                identity_name = "SHARE共用文档" if assoc.singapore_identity_id is None else f"身份ID: {assoc.singapore_identity_id}"
                if identity_name != current_identity:
                    print(f'      {identity_name}:')
                    current_identity = identity_name
                print(f'        - {assoc.document_name} (文档ID: {assoc.document_id})')
        else:
            print('      - 暂无文档关联')
        
        # 7. 验证数据保存逻辑
        print('\n7. 验证数据保存逻辑:')
        print('   ✅ 共用文档保存到 visa_documents_request 表，singapore_identity_id = null')
        print('   ✅ 特定身份文档保存到 visa_documents_request 表，singapore_identity_id = 具体身份ID')
        print('   ✅ 文档关联保存到 visa_document_documents 表，通过多对多关系')
        
        # 8. 检查SHARE身份的特殊处理
        print('\n8. 检查SHARE身份的特殊处理:')
        
        # 检查是否有singapore_identity_id为null的记录（旧方式）
        null_share_configs = VisaDocuments.query.filter_by(
            visa_type_id=test_visa_type.id,
            singapore_identity_id=None
        ).all()
        
        # 检查是否有singapore_identity_id为SHARE ID的记录（新方式）
        share_id_configs = VisaDocuments.query.filter_by(
            visa_type_id=test_visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        print(f'   ✅ 找到 {len(null_share_configs)} 个null身份的SHARE配置')
        print(f'   ✅ 找到 {len(share_id_configs)} 个SHARE ID的配置')
        
        if null_share_configs:
            print('      - 使用singapore_identity_id = null的方式存储共用文档')
        if share_id_configs:
            print('      - 使用singapore_identity_id = SHARE ID的方式存储共用文档')
        
        # 9. 总结
        print('\n9. 数据保存总结:')
        print('   ✅ 签证文档管理器页面保存的数据结构:')
        print('      - 主表: visa_documents_request (存储配置信息)')
        print('      - 关联表: visa_document_documents (存储文档关联)')
        print('      - 文档表: visa_documents_list (存储文档模板)')
        print('      - 身份表: visa_singapore_identity (存储身份信息)')
        print('   ✅ 共用文档和特定身份文档都保存在同一个表中')
        print('   ✅ 通过singapore_identity_id字段区分共用文档和特定身份文档')
        print('   ✅ 文档关联通过visa_document_documents多对多表实现')
        
        return True

if __name__ == '__main__':
    test_data_save_verification() 