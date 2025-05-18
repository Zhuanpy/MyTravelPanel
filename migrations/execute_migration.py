import os
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # 空密码
    'db': 'MyTravelPanel',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def execute_sql_file(filename):
    # 读取SQL文件
    with open(filename, 'r', encoding='utf-8') as f:
        sql_commands = f.read()

    # 连接数据库
    print("Connecting to database with config:", DB_CONFIG)
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            # 执行SQL命令
            for command in sql_commands.split(';'):
                if command.strip():
                    print(f"Executing: {command.strip()}")
                    cursor.execute(command.strip())
        
        # 提交更改
        connection.commit()
        print("Migration executed successfully!")
        
    except Exception as e:
        print(f"Error executing migration: {str(e)}")
        connection.rollback()
        raise
    
    finally:
        connection.close()

if __name__ == '__main__':
    # 执行迁移文件
    execute_sql_file('migrations/recreate_project_refs.sql') 