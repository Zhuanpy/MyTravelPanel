from App import create_app
from App.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaDocumentsList
from App.exts import db
import json

app = create_app()

def test_share_save_fix():
    """测试SHARE身份保存修复"""
    with app.app_context():
        print('=== 测试SHARE身份保存修复 ===')
        
        # 1. 获取测试数据
        print('\n1. 获取测试数据:')
        
        # 获取第一个签证类型
        visa_type = VisaTypes.query.first()
        if not visa_type:
            print('❌ 没有找到签证类型')
            return False
        
        print(f'   签证类型: {visa_type.visa_type} (ID: {visa_type.id})')
        
        # 获取前3个文档
        documents = VisaDocumentsList.query.limit(3).all()
        if len(documents) < 3:
            print('❌ 文档数量不足')
            return False
        
        print(f'   测试文档: {[d.name for d in documents]}')
        
        # 2. 清理现有测试数据
        print('\n2. 清理现有测试数据:')
        
        existing_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
        for doc in existing_docs:
            db.session.delete(doc)
        db.session.commit()
        print(f'   清理了 {len(existing_docs)} 个现有配置')
        
        # 3. 模拟前端发送的数据
        print('\n3. 模拟前端发送的数据:')
        
        # 模拟包含SHARE的配置数据
        identity_configs = [
            {
                'identity_id': None,  # SHARE共用文档
                'document_ids': [doc.id for doc in documents[:2]],  # 前2个文档
                'additional_info': '这是SHARE共用文档的补充信息'
            },
            {
                'identity_id': '1',  # 普通身份
                'document_ids': [doc.id for doc in documents[1:]],  # 后2个文档
                'additional_info': '这是普通身份的补充信息'
            }
        ]
        
        print(f'   配置数据: {json.dumps(identity_configs, indent=2, ensure_ascii=False)}')
        
        # 4. 模拟后端处理逻辑
        print('\n4. 模拟后端处理逻辑:')
        
        try:
            # 处理每个身份配置
            for i, config in enumerate(identity_configs):
                identity_id = config.get('identity_id')
                document_ids = config.get('document_ids', [])
                additional_info = config.get('additional_info', '')
                
                print(f'   处理配置 {i+1}:')
                print(f'     - identity_id: {identity_id} (类型: {type(identity_id)})')
                print(f'     - document_ids: {document_ids}')
                print(f'     - additional_info: {additional_info}')
                
                # 处理identity_id，SHARE身份为null，其他身份为整数
                processed_identity_id = None
                if identity_id == 'SHARE':
                    # SHARE共用文档，设置为null
                    processed_identity_id = None
                    print(f'     - 处理SHARE共用文档配置')
                elif identity_id is not None:
                    try:
                        processed_identity_id = int(identity_id)
                        print(f'     - 转换为整数: {processed_identity_id}')
                    except (ValueError, TypeError):
                        print(f'     - ❌ 无效的identity_id: {identity_id}')
                        continue
                else:
                    # identity_id为null，表示SHARE共用文档
                    processed_identity_id = None
                    print(f'     - 处理SHARE共用文档配置')
                
                print(f'     - 处理后的identity_id: {processed_identity_id} (类型: {type(processed_identity_id)})')
                
                # 创建VisaDocuments记录
                visa_doc = VisaDocuments(
                    visa_type_id=visa_type.id,
                    singapore_identity_id=processed_identity_id,
                    additional_info=additional_info
                )
                db.session.add(visa_doc)
                db.session.flush()
                
                print(f'     - 创建配置记录: ID={visa_doc.id}')
                
                # 设置选中的文档
                if document_ids:
                    selected_docs = VisaDocumentsList.query.filter(VisaDocumentsList.id.in_(document_ids)).all()
                    visa_doc.selected_documents = selected_docs
                    print(f'     - 设置文档: {[d.name for d in selected_docs]}')
                else:
                    visa_doc.selected_documents = []
                    print(f'     - 没有选中文档')
            
            db.session.commit()
            print(f'    ✅ 所有配置保存成功')
            
        except Exception as e:
            print(f'    ❌ 保存失败: {str(e)}')
            db.session.rollback()
            return False
        
        # 5. 验证保存结果
        print('\n5. 验证保存结果:')
        
        saved_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
        print(f'   总共保存了 {len(saved_docs)} 个配置')
        
        for i, doc in enumerate(saved_docs, 1):
            identity_name = "SHARE共用文档" if doc.singapore_identity_id is None else f"身份ID: {doc.singapore_identity_id}"
            doc_names = [d.name for d in doc.selected_documents] if doc.selected_documents else []
            
            print(f'   配置 {i}:')
            print(f'     - 记录ID: {doc.id}')
            print(f'     - 身份: {identity_name}')
            print(f'     - 选中文档: {doc_names}')
            print(f'     - 补充信息: {doc.additional_info}')
        
        # 6. 验证SHARE配置
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=None
        ).first()
        
        if share_doc:
            print(f'\n6. ✅ SHARE配置验证成功:')
            print(f'    - 记录ID: {share_doc.id}')
            print(f'    - 身份ID: {share_doc.singapore_identity_id}')
            print(f'    - 选中文档数: {len(share_doc.selected_documents)}')
            print(f'    - 文档名称: {[d.name for d in share_doc.selected_documents]}')
            print(f'    - 补充信息: {share_doc.additional_info}')
        else:
            print(f'\n6. ❌ 没有找到SHARE配置')
            return False
        
        # 7. 清理测试数据
        print('\n7. 清理测试数据:')
        
        for doc in saved_docs:
            db.session.delete(doc)
        db.session.commit()
        print(f'   清理了 {len(saved_docs)} 个测试配置')
        
        print(f'\n✅ SHARE身份保存修复测试成功！')
        return True

if __name__ == '__main__':
    test_share_save_fix() 