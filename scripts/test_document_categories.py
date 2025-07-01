from App import create_app
from App.models.Visamodels import VisaDocumentsList
from App.exts import db
import json

app = create_app()

def test_document_categories():
    """测试文档分类，检查身份证件类分类中的问题"""
    with app.app_context():
        print('=== 测试文档分类 ===')
        
        # 1. 获取所有文档
        print('\n1. 获取所有文档:')
        all_documents = VisaDocumentsList.query.all()
        print(f'   总文档数量: {len(all_documents)}')
        
        # 2. 按分类统计
        print('\n2. 按分类统计:')
        categories = {}
        for doc in all_documents:
            category = doc.category or '其他'
            if category not in categories:
                categories[category] = []
            categories[category].append(doc)
        
        for category, docs in categories.items():
            print(f'   {category}: {len(docs)} 个文档')
            for doc in docs:
                print(f'     - {doc.name} (ID: {doc.id})')
        
        # 3. 特别检查身份证件类
        print('\n3. 特别检查身份证件类:')
        id_docs = categories.get('身份证件类', [])
        if id_docs:
            print(f'   身份证件类文档数量: {len(id_docs)}')
            for doc in id_docs:
                print(f'     - {doc.name} (ID: {doc.id})')
                if doc.description:
                    print(f'       描述: {doc.description}')
        else:
            print('   ❌ 没有找到身份证件类分类')
        
        # 4. 检查是否有空分类
        print('\n4. 检查空分类:')
        empty_category_docs = [doc for doc in all_documents if not doc.category or doc.category.strip() == '']
        if empty_category_docs:
            print(f'   空分类文档数量: {len(empty_category_docs)}')
            for doc in empty_category_docs:
                print(f'     - {doc.name} (ID: {doc.id})')
        else:
            print('   ✅ 没有空分类的文档')
        
        # 5. 检查分类名称问题
        print('\n5. 检查分类名称问题:')
        category_names = list(categories.keys())
        print(f'   所有分类名称: {category_names}')
        
        # 检查是否有重复或相似的分类名
        similar_categories = []
        for i, cat1 in enumerate(category_names):
            for j, cat2 in enumerate(category_names):
                if i != j and (cat1 in cat2 or cat2 in cat1):
                    similar_categories.append((cat1, cat2))
        
        if similar_categories:
            print('   ⚠️ 发现相似或重复的分类名:')
            for cat1, cat2 in similar_categories:
                print(f'     - {cat1} 与 {cat2}')
        else:
            print('   ✅ 没有发现相似或重复的分类名')
        
        # 6. 检查文档名称问题
        print('\n6. 检查文档名称问题:')
        for category, docs in categories.items():
            if category == '身份证件类':
                print(f'   {category} 分类中的文档:')
                for doc in docs:
                    print(f'     - {doc.name}')
                    # 检查是否有特殊字符或格式问题
                    if any(char in doc.name for char in ['\n', '\r', '\t', '  ']):
                        print(f'       ⚠️ 包含特殊字符或多余空格')
                    if len(doc.name.strip()) != len(doc.name):
                        print(f'       ⚠️ 首尾有空格')
        
        # 7. 模拟前端渲染
        print('\n7. 模拟前端渲染:')
        for category, docs in categories.items():
            if category == '身份证件类':
                print(f'   渲染 {category} 分类:')
                print(f'   <div class="document-category">')
                print(f'     <div class="category-header">')
                print(f'       <h5 class="category-title">')
                print(f'         <i class="fas fa-folder"></i>')
                print(f'         {category}')
                print(f'       </h5>')
                print(f'       <span class="category-count">{len(docs)} 个文档</span>')
                print(f'     </div>')
                print(f'     <div class="category-documents">')
                
                for doc in docs:
                    print(f'       <div class="document-item" data-identity-id="1" data-doc-id="{doc.id}">')
                    print(f'         <input type="checkbox" id="doc_{doc.id}_1" style="display: none;">')
                    print(f'         <label for="doc_{doc.id}_1" style="cursor: pointer; width: 100%;">')
                    print(f'           <i class="fas fa-square" style="margin-right: 8px; color: #ccc;"></i>')
                    print(f'           {doc.name}')
                    print(f'         </label>')
                    print(f'       </div>')
                
                print(f'     </div>')
                print(f'   </div>')
        
        # 8. 总结
        print('\n8. 总结:')
        print(f'   ✅ 总文档数量: {len(all_documents)}')
        print(f'   ✅ 分类数量: {len(categories)}')
        print(f'   ✅ 身份证件类文档数量: {len(id_docs)}')
        
        if id_docs:
            print('   📝 身份证件类文档列表:')
            for doc in id_docs:
                print(f'     - {doc.name}')
        
        return True

if __name__ == '__main__':
    test_document_categories() 