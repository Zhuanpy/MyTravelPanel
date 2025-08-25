"""
签证文档调试工具
"""
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
from ..exts import db


def debug_visa_documents(visa_type_name):
    """调试指定签证类型的文档数据"""
    print(f"\n=== 调试签证类型: {visa_type_name} ===")
    
    # 1. 检查签证类型是否存在
    visa_type = VisaTypes.query.filter_by(visa_type=visa_type_name).first()
    if not visa_type:
        print(f"❌ 签证类型 '{visa_type_name}' 不存在")
        return False
    
    print(f"✅ 签证类型存在 - ID: {visa_type.id}")
    
    # 2. 检查SHARE记录
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    if not share_doc:
        print("❌ SHARE共用资料记录不存在")
        print("🔧 正在创建SHARE记录...")
        
        # 创建SHARE记录
        share_doc = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=None,
            additional_info='共用资料补充信息'
        )
        db.session.add(share_doc)
        db.session.commit()
        print(f"✅ SHARE记录创建成功 - ID: {share_doc.id}")
    else:
        print(f"✅ SHARE记录存在 - ID: {share_doc.id}")
    
    # 3. 检查SHARE记录的关联文档
    print(f"📄 SHARE记录关联的文档数量: {len(share_doc.selected_documents)}")
    if share_doc.selected_documents:
        for doc in share_doc.selected_documents:
            print(f"  - {doc.name} (ID: {doc.id})")
    else:
        print("⚠️ SHARE记录没有关联任何文档")
        print("🔧 正在添加常用共用文档...")
        
        # 添加常用文档
        common_docs = [
            '护照原件', '护照复印件', '近期护照照片', '身份证复印件',
            '出生证明', '学历证明', '工作证明', '银行对账单'
        ]
        
        added_count = 0
        for doc_name in common_docs:
            # 查找或创建文档
            doc = VisaDocumentsList.query.filter_by(name=doc_name).first()
            if not doc:
                doc = VisaDocumentsList(
                    name=doc_name,
                    category='共用资料',
                    description=f'{doc_name}的详细说明'
                )
                db.session.add(doc)
                db.session.flush()
            
            # 添加到SHARE记录
            if doc not in share_doc.selected_documents:
                share_doc.selected_documents.append(doc)
                added_count += 1
        
        db.session.commit()
        print(f"✅ 成功添加 {added_count} 个常用文档")
    
    # 4. 检查特定身份记录
    identity_docs = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id
    ).filter(VisaDocuments.singapore_identity_id.isnot(None)).all()
    
    print(f"👥 特定身份记录数量: {len(identity_docs)}")
    for doc in identity_docs:
        identity_name = doc.singapore_identity.identity_zh if doc.singapore_identity else "未知"
        print(f"  - {identity_name}: {len(doc.selected_documents)} 个文档")
    
    # 5. 测试get_document_info方法
    print("\n🧪 测试get_document_info方法:")
    for doc in identity_docs:
        result = VisaDocuments.get_document_info(visa_type.id, doc.singapore_identity_id)
        print(f"  身份 {doc.singapore_identity.identity_zh}:")
        print(f"    文档信息长度: {len(result.get('document_info', ''))}")
        print(f"    补充信息长度: {len(result.get('additional_info', ''))}")
        
        # 检查是否包含共用资料
        if '【共用资料】' in result.get('document_info', ''):
            print("    ✅ 包含共用资料")
        else:
            print("    ❌ 不包含共用资料")
    
    return True


def fix_share_documents(visa_type_name):
    """修复指定签证类型的SHARE文档问题"""
    print(f"\n=== 修复签证类型: {visa_type_name} ===")
    
    visa_type = VisaTypes.query.filter_by(visa_type=visa_type_name).first()
    if not visa_type:
        print(f"❌ 签证类型 '{visa_type_name}' 不存在")
        return False
    
    # 确保SHARE记录存在
    share_doc = VisaDocuments.query.filter_by(
        visa_type_id=visa_type.id,
        singapore_identity_id=None
    ).first()
    
    if not share_doc:
        share_doc = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=None,
            additional_info='共用资料补充信息'
        )
        db.session.add(share_doc)
        db.session.commit()
        print(f"✅ 创建SHARE记录 - ID: {share_doc.id}")
    
    # 确保有基本的共用文档
    basic_docs = [
        {'name': '护照原件', 'category': '共用资料'},
        {'name': '护照复印件', 'category': '共用资料'},
        {'name': '近期护照照片', 'category': '共用资料'},
        {'name': '身份证复印件', 'category': '共用资料'},
        {'name': '申请表', 'category': '共用资料'}
    ]
    
    added_count = 0
    for doc_info in basic_docs:
        # 查找或创建文档
        doc = VisaDocumentsList.query.filter_by(name=doc_info['name']).first()
        if not doc:
            doc = VisaDocumentsList(
                name=doc_info['name'],
                category=doc_info['category'],
                description=f"{doc_info['name']}的详细说明"
            )
            db.session.add(doc)
            db.session.flush()
        
        # 添加到SHARE记录
        if doc not in share_doc.selected_documents:
            share_doc.selected_documents.append(doc)
            added_count += 1
    
    db.session.commit()
    print(f"✅ 修复完成，添加了 {added_count} 个文档")
    
    return True


def check_all_visa_types():
    """检查所有签证类型的SHARE记录"""
    print("\n=== 检查所有签证类型的SHARE记录 ===")
    
    visa_types = VisaTypes.query.all()
    print(f"📋 总共有 {len(visa_types)} 个签证类型")
    
    missing_share = []
    for vt in visa_types:
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=vt.id,
            singapore_identity_id=None
        ).first()
        
        if not share_doc:
            missing_share.append(vt.visa_type)
            print(f"❌ {vt.visa_type} - 缺少SHARE记录")
        else:
            doc_count = len(share_doc.selected_documents)
            if doc_count == 0:
                print(f"⚠️ {vt.visa_type} - SHARE记录存在但无文档")
            else:
                print(f"✅ {vt.visa_type} - SHARE记录正常 ({doc_count}个文档)")
    
    if missing_share:
        print(f"\n🔧 需要修复的签证类型: {', '.join(missing_share)}")
        return missing_share
    else:
        print("\n✅ 所有签证类型的SHARE记录都正常")
        return []


def create_missing_share_records():
    """为所有缺少SHARE记录的签证类型创建记录"""
    missing_types = check_all_visa_types()
    
    if not missing_types:
        return
    
    print(f"\n🔧 正在为 {len(missing_types)} 个签证类型创建SHARE记录...")
    
    for visa_type_name in missing_types:
        try:
            fix_share_documents(visa_type_name)
        except Exception as e:
            print(f"❌ 修复 {visa_type_name} 时出错: {str(e)}")
    
    print("✅ 批量修复完成")


if __name__ == "__main__":
    # 可以在这里添加测试代码
    pass
