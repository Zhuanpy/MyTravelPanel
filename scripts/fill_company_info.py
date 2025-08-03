import os
import time
import random
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from fake_useragent import UserAgent
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# 初始化日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('company_info_filler.log'),
            logging.StreamHandler()
        ]
    )

# 数据库配置
DB_USER = "root"
DB_PASSWORD = "***REMOVED***"
DB_HOST = "localhost"
DB_NAME = "travelindustry"
TABLE_NAME = "customer_companies"

# 需要补全的字段 - 修正为与数据库字段一致
FIELDS = ["address", "contact_phone", "legal_person"]

# 伪造浏览器UA
ua = UserAgent()

# 真实的浏览器头信息列表
BROWSER_HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
]

def get_engine():
    return create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
    )

def get_companies_missing_info():
    engine = get_engine()
    with engine.connect() as conn:
        sql = f"SELECT id, company_name, address, contact_phone, legal_person FROM {TABLE_NAME}"
        result = conn.execute(text(sql))
        companies = []
        for row in result:
            # 判断是否有字段缺失
            if any(row[field] is None or str(row[field]).strip() == "" for field in FIELDS):
                companies.append(dict(row))
        return companies

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

def create_driver():
    """创建Chrome WebDriver"""
    chrome_options = Options()
    
    # 设置Chrome选项
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 随机窗口大小
    width = random.randint(1200, 1920)
    height = random.randint(800, 1080)
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    # 随机User-Agent
    user_agent = ua.random
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # 禁用图片加载以提高速度
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # 执行脚本来隐藏webdriver属性
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"创建WebDriver失败: {e}")
        return None

def search_recordowl_info_selenium(company_name, max_retries=2):
    """使用Selenium从recordowl.com爬取公司信息"""
    # 生成URL
    url_name = normalize_company_name_for_url(company_name)
    url = f"https://recordowl.com/company/{url_name}"
    
    driver = None
    try:
        driver = create_driver()
        if not driver:
            print("无法创建WebDriver")
            return {}
        
        print(f"正在访问: {url}")
        
        # 先访问主页
        print("访问主页...")
        driver.get("https://recordowl.com/")
        time.sleep(random.uniform(2, 4))
        
        # 模拟用户行为：滚动页面
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(1, 2))
        
        # 访问目标页面
        print(f"访问公司页面: {url}")
        driver.get(url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            print("页面加载超时")
            return {}
        
        # 模拟用户行为：滚动页面
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(random.uniform(1, 2))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight*2/3);")
        time.sleep(random.uniform(1, 2))
        
        # 获取页面内容
        page_source = driver.page_source
        
        # 保存调试文件
        debug_file = f"debug_recordowl_{url_name}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(page_source)
        print(f"页面内容已保存到: {debug_file}")
        
        # 解析页面内容
        soup = BeautifulSoup(page_source, "html.parser")
        
        # 尝试多种方式查找信息
        info = {}
        
        # 定义要查找的字段
        target_fields = {
            "Registration Number": "registration_number",
            "Registered Address": "address", 
            "Operating Status": "operating_status",
            "Company Age": "company_age",
            "Contact Number": "contact_phone"
        }
        
        # 方法1: 查找表格中的信息
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    # 检查是否匹配目标字段
                    for field_name, field_key in target_fields.items():
                        if field_name.lower() in key.lower() and value:
                            info[field_key] = value
                            print(f"找到 {field_name}: {value}")
        
        # 方法2: 查找特定class或id的元素
        for field_name, field_key in target_fields.items():
            if not info.get(field_key):
                # 查找包含字段名的元素
                elements = soup.find_all(text=re.compile(field_name, re.I))
                for elem in elements:
                    parent = elem.parent
                    if parent:
                        # 查找相邻的兄弟元素或父元素中的值
                        next_sibling = parent.find_next_sibling()
                        if next_sibling:
                            value = next_sibling.get_text(strip=True)
                            if value and value != field_name:
                                info[field_key] = value
                                print(f"通过相邻元素找到 {field_name}: {value}")
                                break
        
        # 方法3: 使用Selenium直接查找元素
        try:
            for field_name, field_key in target_fields.items():
                if not info.get(field_key):
                    # 查找包含字段名的元素
                    xpath = f"//*[contains(text(), '{field_name}')]"
                    elements = driver.find_elements(By.XPATH, xpath)
                    
                    for elem in elements:
                        # 获取父元素或相邻元素的值
                        parent = elem.find_element(By.XPATH, "./..")
                        siblings = parent.find_elements(By.XPATH, "./*")
                        
                        for sibling in siblings:
                            text = sibling.text.strip()
                            if text and text != field_name and len(text) > 3:
                                info[field_key] = text
                                print(f"通过Selenium找到 {field_name}: {text}")
                                break
                        if field_key in info:
                            break
        except Exception as e:
            print(f"Selenium查找失败: {e}")
        
        # 方法4: 查找所有包含关键词的文本块
        for field_name, field_key in target_fields.items():
            if not info.get(field_key):
                # 查找包含字段名的文本块
                text_blocks = soup.find_all(text=re.compile(field_name, re.I))
                for text_block in text_blocks:
                    # 获取包含该文本的完整元素
                    container = text_block.parent
                    if container:
                        full_text = container.get_text()
                        # 尝试提取字段值
                        pattern = rf"{field_name}[:\s]*([^,\n\r]+)"
                        match = re.search(pattern, full_text, re.I)
                        if match:
                            value = match.group(1).strip()
                            if value and value != field_name:
                                info[field_key] = value
                                print(f"通过文本模式找到 {field_name}: {value}")
                                break
        
        print(f"找到的信息: {info}")
        return info
        
    except Exception as e:
        print(f"Selenium爬取失败: {e}")
        return {}
        
    finally:
        if driver:
            driver.quit()

def update_company_info(company_id, info):
    """更新公司信息到数据库"""
    engine = get_engine()
    with engine.begin() as conn:  # 使用begin()来自动处理事务
        try:
            fields = []
            values = {}
            
            # 字段映射：将爬取的信息映射到数据库字段
            field_mapping = {
                "address": "address",  # Registered Address -> address
                "contact_phone": "contact_phone",  # Contact Number -> contact_phone
                "registration_number": "company_code",  # Registration Number -> company_code
                "operating_status": "status",  # Operating Status -> status
                "company_age": "remarks"  # Company Age -> remarks (作为备注)
            }
            
            for info_key, db_field in field_mapping.items():
                if info_key in info and info[info_key]:
                    if db_field in FIELDS:  # 只更新需要的字段
                        fields.append(f"{db_field} = :{db_field}")
                        values[db_field] = info[info_key]
                    else:
                        # 对于不在FIELDS中的字段，添加到remarks
                        if "remarks" not in values:
                            values["remarks"] = ""
                        values["remarks"] += f"{info_key}: {info[info_key]}; "
            
            if fields:
                sql = f"UPDATE {TABLE_NAME} SET {', '.join(fields)} WHERE id = :id"
                values["id"] = company_id
                conn.execute(text(sql), values)
                print(f"数据库更新成功: {values}")
            else:
                print("没有有效信息需要更新")
                
        except Exception as e:
            print(f"数据库更新失败: {e}")
            raise  # 重新抛出异常，让with语句处理回滚

def test_single_company(company_name):
    """测试单个公司的爬取功能"""
    print(f"测试公司: {company_name}")
    info = search_recordowl_info_selenium(company_name)
    if info:
        print(f"成功获取信息: {info}")
    else:
        print("未找到信息")

def main():
    print("开始爬取公司信息...")
    
    # 测试单个公司
    test_company = "BAONENG ENGINEERING PTE. LTD."
    test_single_company(test_company)
    
    # 询问是否继续批量处理
    response = input("\n是否继续批量处理所有公司? (y/n): ")
    if response.lower() != 'y':
        return
    
    companies = get_companies_missing_info()
    print(f"共需补全信息的公司：{len(companies)}")
    
    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] 正在处理：{company['company_name']}")
        info = search_recordowl_info_selenium(company['company_name'])
        
        if info:
            update_company_info(company['id'], info)
            print(f"已更新：{company['company_name']} -> {info}")
        else:
            print(f"未找到信息：{company['company_name']}")
        
        # 随机延时
        delay = random.uniform(3, 6)
        print(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)

if __name__ == "__main__":
    main()
