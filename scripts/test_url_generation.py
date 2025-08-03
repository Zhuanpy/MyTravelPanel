import re

def normalize_company_name_for_url(company_name):
    """将公司名转换为recordowl.com的URL格式"""
    # 保留完整公司名，只替换特殊字符
    name = company_name.upper()
    
    # 替换特殊字符：空格和点号替换为连字符
    name = re.sub(r'[^A-Za-z0-9\s\.]+', ' ', name)  # 保留点号，其他特殊字符替换为空格
    name = re.sub(r'[\s\.]+', '-', name.strip())  # 空格和点号都替换为连字符
    name = name.lower()
    
    # 移除开头和结尾的连字符
    name = name.strip('-')
    
    return name

# 测试
test_company = "BAONENG ENGINEERING PTE. LTD."
result = normalize_company_name_for_url(test_company)
print(f"原始公司名: {test_company}")
print(f"生成的URL: {result}")
print(f"完整URL: https://recordowl.com/company/{result}") 