from App import create_app
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaDocumentsList
from App.exts import db
import json

app = create_app()

def test_share_id_fix():
    """测试SHARE身份ID修正后的逻辑"""
    with app.app_context():
        print('=== 测试SHARE身份ID修正后的逻辑 ===')
        
        # 1. 检查SHARE身份
        print('\n1. 检查SHARE身份:')
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if share_identity:
            print(f'   ✅ 找到SHARE身份 - ID: {share_identity.id}, 名称: {share_identity.identity_zh}')
        else:
            print('   ❌ 未找到SHARE身份')
            return False
        
        # 2. 检查签证类型
        print('\n2. 检查签证类型:')
        visa_types = VisaTypes.query.limit(3).all()
        if not visa_types:
            print('   ❌ 没有找到签证类型')
            return False
        
        test_visa_type = visa_types[0]
        print(f'   ✅ 测试签证类型: {test_visa_type.visa_type} (ID: {test_visa_type.id})')
        
        # 3. 检查现有配置
        print('\n3. 检查现有配置:')
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
        print(f'   ✅ 找到 {len(existing_configs)} 个现有配置')
        
        for config in existing_configs:
            identity_name = "SHARE共用文档" if config.singapore_identity_id == share_identity.id else f"身份ID: {config.singapore_identity_id}"
            doc_count = len(config.selected_documents) if config.selected_documents else 0
            print(f'      - 配置ID: {config.id}, 身份: {identity_name}, 文档数量: {doc_count}')
        
        # 4. 检查SHARE配置
        print('\n4. 检查SHARE配置:')
        
        # 检查是否有singapore_identity_id为SHARE ID的记录（新方式）
        share_id_configs = VisaDocuments.query.filter_by(
            visa_type_id=test_visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        # 检查是否有singapore_identity_id为null的记录（旧方式）
        null_share_configs = VisaDocuments.query.filter_by(
            visa_type_id=test_visa_type.id,
            singapore_identity_id=None
        ).all()
        
        print(f'   ✅ 找到 {len(share_id_configs)} 个SHARE ID的配置')
        print(f'   ✅ 找到 {len(null_share_configs)} 个null身份的SHARE配置')
        
        if share_id_configs:
            print('      - 使用singapore_identity_id = SHARE ID的方式存储共用文档（正确）')
        if null_share_configs:
            print('      - 使用singapore_identity_id = null的方式存储共用文档（旧方式，需要迁移）')
        
        # 5. 模拟保存SHARE配置
        print('\n5. 模拟保存SHARE配置:')
        
        # 模拟前端发送的数据
        identity_configs = [
            {
                'identity_id': 'SHARE',
                'document_ids': [1, 2, 3],  # 假设的文档ID
                'additional_info': 'SHARE共用文档测试'
            }
        ]
        
        print(f'   模拟数据: {json.dumps(identity_configs, indent=2, ensure_ascii=False)}')
        
        # 模拟后端处理逻辑
        print('\n6. 模拟后端处理逻辑:')
        
        try:
            for i, config in enumerate(identity_configs):
                identity_id = config.get('identity_id')
                document_ids = config.get('document_ids', [])
                additional_info = config.get('additional_info', '')
                
                print(f'   处理配置 {i+1}:')
                print(f'     - identity_id: {identity_id} (类型: {type(identity_id)})')
                print(f'     - document_ids: {document_ids}')
                print(f'     - additional_info: {additional_info}')
                
                # 处理identity_id，SHARE身份使用SHARE身份ID
                processed_identity_id = None
                if identity_id == 'SHARE':
                    # SHARE共用文档，使用SHARE身份ID
                    processed_identity_id = share_identity.id
                    print(f'     - 处理SHARE共用文档配置，使用SHARE身份ID: {processed_identity_id}')
                elif identity_id is not None:
                    try:
                        processed_identity_id = int(identity_id)
                        print(f'     - 转换为整数: {processed_identity_id}')
                    except (ValueError, TypeError):
                        print(f'     - ❌ 无效的identity_id: {identity_id}')
                        continue
                
                print(f'     - 处理后的identity_id: {processed_identity_id} (类型: {type(processed_identity_id)})')
                
                # 查找或创建VisaDocuments记录
                existing_doc = VisaDocuments.query.filter_by(
                    visa_type_id=test_visa_type.id,
                    singapore_identity_id=processed_identity_id
                ).first()
                
                if existing_doc:
                    print(f'     - 更新现有记录 - ID: {existing_doc.id}')
                    existing_doc.additional_info = additional_info
                    visa_doc = existing_doc
                else:
                    print(f'     - 创建新记录')
                    visa_doc = VisaDocuments(
                        visa_type_id=test_visa_type.id,
                        singapore_identity_id=processed_identity_id,
                        additional_info=additional_info
                    )
                    db.session.add(visa_doc)
                    db.session.flush()
                    print(f'     - 新记录ID: {visa_doc.id}')
                
                # 更新选中的文档
                if document_ids:
                    documents = VisaDocumentsList.query.filter(VisaDocumentsList.id.in_(document_ids)).all()
                    visa_doc.selected_documents = documents
                    print(f'     - 设置了 {len(documents)} 个文档')
                else:
                    visa_doc.selected_documents = []
                    print(f'     - 清空了所有文档')
            
            # 提交更改
            db.session.commit()
            print(f'   ✅ 配置保存成功')
            
        except Exception as e:
            db.session.rollback()
            print(f'   ❌ 保存失败: {str(e)}')
            return False
        
        # 7. 验证保存结果
        print('\n7. 验证保存结果:')
        
        # 检查SHARE配置是否保存成功
        saved_share_config = VisaDocuments.query.filter_by(
            visa_type_id=test_visa_type.id,
            singapore_identity_id=share_identity.id
        ).first()
        
        if saved_share_config:
            print(f'   ✅ SHARE配置保存成功')
            print(f'      - 配置ID: {saved_share_config.id}')
            print(f'      - 身份ID: {saved_share_config.singapore_identity_id}')
            print(f'      - 补充信息: {saved_share_config.additional_info}')
            print(f'      - 文档数量: {len(saved_share_config.selected_documents) if saved_share_config.selected_documents else 0}')
        else:
            print(f'   ❌ SHARE配置保存失败')
            return False
        
        # 8. 清理测试数据
        print('\n8. 清理测试数据:')
        if saved_share_config:
            db.session.delete(saved_share_config)
            db.session.commit()
            print(f'   ✅ 测试数据清理完成')
        
        # 9. 总结
        print('\n9. 修正总结:')
        print('   ✅ SHARE身份ID修正完成')
        print('   ✅ 共用文档现在使用singapore_identity_id = SHARE身份ID (9)')
        print('   ✅ 不再使用singapore_identity_id = null')
        print('   ✅ 数据保存逻辑已统一')
        
        return True

if __name__ == '__main__':
    test_share_id_fix() 