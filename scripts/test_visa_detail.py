import requests

# 测试visa_detail路由
url = "http://localhost:5000/visa/project/visa_detail/id/276"
print(f"测试URL: {url}")

try:
    response = requests.get(url, allow_redirects=False)
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 302:
        print(f"重定向到: {response.headers.get('Location')}")
    elif response.status_code == 200:
        print("成功访问页面")
    else:
        print(f"响应内容: {response.text[:500]}...")
        
except Exception as e:
    print(f"请求失败: {e}")

print("\n" + "="*50)
print("测试签证介绍路由")
print("="*50)

# 测试签证介绍路由
visa_intro_url = "http://localhost:5000/visa/intro/中国签证"
print(f"测试签证介绍URL: {visa_intro_url}")

try:
    response = requests.get(visa_intro_url, allow_redirects=False)
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 302:
        print(f"重定向到: {response.headers.get('Location')}")
    elif response.status_code == 200:
        print("成功访问签证介绍页面")
        print("页面内容长度:", len(response.text))
        if "签证介绍" in response.text:
            print("✓ 页面包含'签证介绍'标题")
        if "费用说明" in response.text:
            print("✓ 页面包含'费用说明'部分")
        if "处理时间" in response.text:
            print("✓ 页面包含'处理时间'部分")
        if "申请资料" in response.text:
            print("✓ 页面包含'申请资料'部分")
    else:
        print(f"响应内容: {response.text[:500]}...")
        
except Exception as e:
    print(f"请求失败: {e}")

print("\n" + "="*50)
print("测试签证介绍路由 - 不存在的签证类型")
print("="*50)

# 测试不存在的签证类型
invalid_visa_intro_url = "http://localhost:5000/visa/intro/不存在的签证类型"
print(f"测试无效签证介绍URL: {invalid_visa_intro_url}")

try:
    response = requests.get(invalid_visa_intro_url, allow_redirects=False)
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 302:
        print(f"重定向到: {response.headers.get('Location')}")
        print("✓ 正确处理了不存在的签证类型")
    elif response.status_code == 200:
        print("成功访问页面（可能是默认页面）")
    else:
        print(f"响应内容: {response.text[:500]}...")
        
except Exception as e:
    print(f"请求失败: {e}") 