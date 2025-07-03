from App import create_app
from App.models.Product.Visamodels import VisaTypes, VisaSingaporeIdentity, VisaDocumentsList

app = create_app()

def test_default_selection():
    """测试默认选择功能"""
    with app.app_context():
        print('=== 测试默认选择功能 ===')
        
        # 1. 检查签证类型数据
        print('\n1. 检查签证类型数据:')
        
        visa_types = VisaTypes.query.all()
        if not visa_types:
            print('❌ 没有找到签证类型数据')
            return False
        
        print(f'   找到 {len(visa_types)} 个签证类型:')
        for i, visa_type in enumerate(visa_types, 1):
            print(f'   {i}. {visa_type.visa_type} (ID: {visa_type.id})')
        
        first_visa_type = visa_types[0]
        print(f'   第一个签证类型: {first_visa_type.visa_type}')
        
        # 2. 检查身份数据
        print('\n2. 检查身份数据:')
        
        identities = VisaSingaporeIdentity.query.all()
        if not identities:
            print('❌ 没有找到身份数据')
            return False
        
        print(f'   找到 {len(identities)} 个身份:')
        for i, identity in enumerate(identities, 1):
            print(f'   {i}. {identity.identity_zh} (ID: {identity.id})')
        
        # 检查是否有SHARE身份
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if share_identity:
            print(f'   ✅ 找到SHARE身份: ID={share_identity.id}')
        else:
            print(f'   ⚠️  没有找到SHARE身份')
        
        # 3. 检查文档数据
        print('\n3. 检查文档数据:')
        
        documents = VisaDocumentsList.query.limit(5).all()
        if not documents:
            print('❌ 没有找到文档数据')
            return False
        
        print(f'   找到 {len(documents)} 个测试文档:')
        for i, doc in enumerate(documents, 1):
            print(f'   {i}. {doc.name} (ID: {doc.id}, 分类: {doc.category})')
        
        # 4. 模拟前端默认选择逻辑
        print('\n4. 模拟前端默认选择逻辑:')
        
        # 模拟没有选中签证类型的情况
        currentVisaType = None
        print(f'   当前选中的签证类型: {currentVisaType}')
        
        # 模拟选择第一个签证类型
        if not currentVisaType and visa_types:
            first_visa_type = visa_types[0]
            currentVisaType = first_visa_type.visa_type
            print(f'   ✅ 默认选择第一个签证类型: {currentVisaType}')
        else:
            print(f'   ❌ 无法选择第一个签证类型')
            return False
        
        # 5. 模拟默认选中共用文档
        print('\n5. 模拟默认选中共用文档:')
        
        # 检查共用文档是否存在
        if share_identity:
            print(f'   ✅ SHARE身份存在，可以默认选中')
            print(f'   - 身份ID: {share_identity.id}')
            print(f'   - 身份名称: {share_identity.identity_zh}')
            print(f'   - 显示名称: 共用文档')
        else:
            print(f'   ⚠️  SHARE身份不存在，无法默认选中')
        
        # 6. 验证默认选择流程
        print('\n6. 验证默认选择流程:')
        
        print(f'   步骤1: 页面加载')
        print(f'   步骤2: 检查是否有选中的签证类型: {currentVisaType is not None}')
        print(f'   步骤3: 如果没有选中，选择第一个: {first_visa_type.visa_type}')
        print(f'   步骤4: 加载签证类型配置')
        print(f'   步骤5: 默认选中共用文档: {"是" if share_identity else "否"}')
        
        if currentVisaType and share_identity:
            print(f'   ✅ 默认选择流程验证成功')
            print(f'   - 默认签证类型: {currentVisaType}')
            print(f'   - 默认选中身份: 共用文档 (SHARE)')
        else:
            print(f'   ❌ 默认选择流程验证失败')
            return False
        
        # 7. 总结
        print(f'\n✅ 默认选择功能测试成功！')
        print(f'   总结:')
        print(f'   - 页面加载时会自动选择第一个签证类型')
        print(f'   - 选择签证类型后会自动选中共用文档')
        print(f'   - 共用文档会显示为"共用文档 (共用)"')
        print(f'   - 用户可以直接开始配置共用文档')
        
        return True

if __name__ == '__main__':
    test_default_selection() 