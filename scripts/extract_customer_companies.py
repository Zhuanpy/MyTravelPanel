import os
import pandas as pd
from sqlalchemy import create_engine
import sys

# 动态导入App/config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from App.config import Config

# 自动获取账单目录
BILLING_PATH = str(Config.BILLING_DATA_PATH / "BOOKING" / "Zz" / "HID")

# 数据库配置
DB_CONFIG = {
    'host': Config.DB_HOST,
    'user': Config.DB_USER,
    'password': Config.DB_PASSWORD,
    'database': Config.DB_NAME
}

def get_excel_files(directory):
    excel_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.xls'):
                excel_files.append(os.path.join(root, file))
    return excel_files

def extract_companies(excel_files):
    companies = set()
    for file in excel_files:
        try:
            ext = os.path.splitext(file)[-1].lower()
            if ext == ".xls":
                df = pd.read_excel(file, header=None, engine="xlrd")
            else:
                df = pd.read_excel(file, header=None, engine="openpyxl")
            # 直接取第二列（B列，索引为1）
            company_col = df.iloc[:, 1]
            companies.update(company_col.dropna().astype(str).str.strip().unique())
        except Exception as e:
            print(f"Error processing {file}: {e}")
    return sorted(companies)

def save_to_mysql(companies):
    """Save companies to MySQL database"""
    engine = create_engine(
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    )
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS customer_companies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    with engine.connect() as conn:
        conn.execute(create_table_sql)
    for company in companies:
        try:
            insert_sql = f"""
            INSERT IGNORE INTO customer_companies (company_name)
            VALUES ('{company.replace("'", "''")}')
            """
            with engine.connect() as conn:
                conn.execute(insert_sql)
        except Exception as e:
            print(f"Error inserting {company}: {str(e)}")

if __name__ == "__main__":
    print(f"账单目录自动检测为: {BILLING_PATH}")
    excel_files = get_excel_files(BILLING_PATH)
    if not excel_files:
        print("No Excel files found in directory")
    else:
        print(f"Found {len(excel_files)} Excel files")
        companies = extract_companies(excel_files)
        print(f"Extracted {len(companies)} unique companies")
        save_to_mysql(companies)
        print("Companies saved to database")