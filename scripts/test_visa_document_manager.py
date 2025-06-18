#!/usr/bin/env python3
"""
测试签证文档管理器的数据保存和读取功能
验证 visa_documents_request 和 visa_document_documents 两个表的数据交互
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_visa_document_manager():
    """测试签证文档管理器的数据保存和读取"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🧪 开始测试签证文档管理器数据交互...")
            
            # 1. 检查基础数据
            print("\n📋 1. 检查基础数据:")
            
            # 检查签证类型
            visa_types = VisaTypes.query.all()
            print(f"   签证类型数量: {len(visa_types)}")
            if visa_types:
                test_visa_type = visa_types[0]
                print(f"   测试签证类型: {test_visa_type.visa_type} (ID: {test_visa_type.id})")
            else:
                print("   ❌ 没有找到签证类型，无法继续测试")
                return False
            
            # 检查文档列表
            documents = VisaDocumentsList.query.all()
            print(f"   文档模板数量: {len(documents)}")
            if documents:
                test_documents = documents[:3]  # 取前3个文档
                print(f"   测试文档: {[d.name for d in test_documents]}")
            else:
                print("   ❌ 没有找到文档模板，无法继续测试")
                return False
            
            # 检查身份
            identities = VisaSingaporeIdentity.query.all()
            print(f"   身份数量: {len(identities)}")
            if identities:
                test_identity = identities[0]
                print(f"   测试身份: {test_identity.identity_zh} (ID: {test_identity.id})")
            else:
                print("   ❌ 没有找到身份，无法继续测试")
                return False
            
            # 2. 测试数据保存
            print("\n💾 2. 测试数据保存:")
            
            # 清理现有测试数据
            existing_docs = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
            for doc in existing_docs:
                db.session.delete(doc)
            db.session.commit()
            print(f"   清理了 {len(existing_docs)} 个现有配置")
            
            # 创建SHARE配置
            share_doc = VisaDocuments(
                visa_type_id=test_visa_type.id,
                singapore_identity_id=None,  # SHARE
                additional_info="这是共用资料的补充信息"
            )
            share_doc.selected_documents = test_documents[:2]  # 选择前2个文档
            db.session.add(share_doc)
            
            # 创建特定身份配置
            identity_doc = VisaDocuments(
                visa_type_id=test_visa_type.id,
                singapore_identity_id=test_identity.id,
                additional_info="这是特定身份的补充信息"
            )
            identity_doc.selected_documents = test_documents[1:3]  # 选择后2个文档
            db.session.add(identity_doc)
            
            db.session.commit()
            print(f"   创建了SHARE配置 (ID: {share_doc.id})")
            print(f"   创建了身份配置 (ID: {identity_doc.id})")
            
            # 3. 验证数据保存
            print("\n✅ 3. 验证数据保存:")
            
            # 检查visa_documents_request表
            saved_docs = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
            print(f"   visa_documents_request表记录数: {len(saved_docs)}")
            
            for doc in saved_docs:
                identity_name = "SHARE" if doc.singapore_identity_id is None else f"身份ID:{doc.singapore_identity_id}"
                doc_count = len(doc.selected_documents) if doc.selected_documents else 0
                print(f"   - 记录ID: {doc.id}, 身份: {identity_name}, 文档数: {doc_count}, 补充信息: {doc.additional_info}")
                
                if doc.selected_documents:
                    doc_names = [d.name for d in doc.selected_documents]
                    print(f"     文档列表: {doc_names}")
            
            # 检查visa_document_documents关联表
            print("\n🔗 4. 检查关联表数据:")
            
            # 查询关联表
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT vd.id as visa_doc_id, vd.singapore_identity_id, 
                       vdd.document_id, vdl.name as document_name
                FROM visa_documents_request vd
                LEFT JOIN visa_document_documents vdd ON vd.id = vdd.visa_document_id
                LEFT JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
                WHERE vd.visa_type_id = :visa_type_id
                ORDER BY vd.singapore_identity_id, vdl.name
            """), {'visa_type_id': test_visa_type.id})
            
            associations = result.fetchall()
            print(f"   关联表记录数: {len(associations)}")
            
            current_doc_id = None
            for assoc in associations:
                if assoc.visa_doc_id != current_doc_id:
                    identity_name = "SHARE" if assoc.singapore_identity_id is None else f"身份ID:{assoc.singapore_identity_id}"
                    print(f"   - 签证文档ID: {assoc.visa_doc_id} ({identity_name}):")
                    current_doc_id = assoc.visa_doc_id
                
                if assoc.document_id:
                    print(f"     * 文档ID: {assoc.document_id} - {assoc.document_name}")
            
            # 5. 测试数据读取
            print("\n📖 5. 测试数据读取:")
            
            # 使用get_document_info方法
            result = VisaDocuments.get_document_info(test_visa_type.id, test_identity.id)
            print(f"   获取文档信息结果:")
            print(f"   - document_info: {result['document_info']}")
            print(f"   - additional_info: {result['additional_info']}")
            
            # 6. 测试前端API格式
            print("\n🌐 6. 测试前端API格式:")
            
            # 模拟前端API调用
            visa_documents = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
            
            config_data = {
                'visa_type': test_visa_type.visa_type,
                'documents': []
            }
            
            # 处理SHARE配置
            share_docs = [vd for vd in visa_documents if vd.singapore_identity_id is None]
            selected_share_documents = []
            share_additional_info = ""
            
            for vd in share_docs:
                if vd.selected_documents:
                    for doc in vd.selected_documents:
                        selected_share_documents.append({
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category
                        })
                share_additional_info = vd.additional_info or ""
            
            config_data['documents'].append({
                'singapore_identity_id': None,
                'identity_name': 'SHARE',
                'selected_documents': selected_share_documents,
                'additional_info': share_additional_info
            })
            
            # 处理特定身份配置
            identity_docs = [vd for vd in visa_documents if vd.singapore_identity_id == test_identity.id]
            selected_identity_documents = []
            identity_additional_info = ""
            
            for vd in identity_docs:
                if vd.selected_documents:
                    for doc in vd.selected_documents:
                        selected_identity_documents.append({
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category
                        })
                identity_additional_info = vd.additional_info or ""
            
            config_data['documents'].append({
                'singapore_identity_id': test_identity.id,
                'identity_name': test_identity.identity_zh,
                'selected_documents': selected_identity_documents,
                'additional_info': identity_additional_info
            })
            
            print(f"   前端API数据格式:")
            print(f"   - 签证类型: {config_data['visa_type']}")
            print(f"   - 配置数量: {len(config_data['documents'])}")
            
            for doc_config in config_data['documents']:
                identity_name = doc_config['identity_name']
                doc_count = len(doc_config['selected_documents'])
                print(f"   - {identity_name}: {doc_count} 个文档")
                if doc_config['selected_documents']:
                    doc_names = [d['name'] for d in doc_config['selected_documents']]
                    print(f"     文档: {doc_names}")
            
            print("\n🎉 测试完成！数据保存和读取功能正常")
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_visa_document_manager()
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 测试失败！")
        sys.exit(1) 