from App import create_app
from App.models.Product.Visamodels import VisaDocumentsList
from App.exts import db

app = create_app()

def fix_document_categories():
    """修复文档分类中的制表符和空格问题"""
    with app.app_context():
        print('=== 修复文档分类问题 ===')
        
        # 1. 查找有问题的分类
        print('\n1. 查找有问题的分类:')
        all_documents = VisaDocumentsList.query.all()
        
        problematic_docs = []
        for doc in all_documents:
            if doc.category and ('\t' in doc.category or doc.category.strip() != doc.category):
                problematic_docs.append(doc)
                print(f'   发现问题文档: "{doc.name}" - 分类: "{repr(doc.category)}"')
        
        if not problematic_docs:
            print('   ✅ 没有发现分类问题')
            return True
        
        # 2. 修复分类名称
        print(f'\n2. 修复 {len(problematic_docs)} 个文档的分类:')
        fixed_count = 0
        
        for doc in problematic_docs:
            original_category = doc.category
            # 移除制表符和首尾空格
            fixed_category = doc.category.strip().replace('\t', '')
            
            if fixed_category != original_category:
                print(f'   修复: "{doc.name}"')
                print(f'     原分类: "{repr(original_category)}"')
                print(f'     新分类: "{fixed_category}"')
                
                doc.category = fixed_category
                fixed_count += 1
        
        # 3. 保存更改
        if fixed_count > 0:
            try:
                db.session.commit()
                print(f'\n3. 成功修复 {fixed_count} 个文档的分类')
            except Exception as e:
                db.session.rollback()
                print(f'\n❌ 保存失败: {e}')
                return False
        else:
            print('\n3. 无需修复')
        
        # 4. 验证修复结果
        print('\n4. 验证修复结果:')
        all_documents_after = VisaDocumentsList.query.all()
        categories_after = {}
        
        for doc in all_documents_after:
            category = doc.category or '其他'
            if category not in categories_after:
                categories_after[category] = []
            categories_after[category].append(doc)
        
        print('   修复后的分类:')
        for category, docs in categories_after.items():
            print(f'     {category}: {len(docs)} 个文档')
        
        # 检查是否还有问题
        still_problematic = []
        for doc in all_documents_after:
            if doc.category and ('\t' in doc.category or doc.category.strip() != doc.category):
                still_problematic.append(doc)
        
        if still_problematic:
            print(f'   ⚠️ 仍有 {len(still_problematic)} 个文档有问题')
            for doc in still_problematic:
                print(f'     - {doc.name}: "{repr(doc.category)}"')
        else:
            print('   ✅ 所有分类问题已修复')
        
        return True

if __name__ == '__main__':
    fix_document_categories() 