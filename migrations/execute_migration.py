"""
执行SQL迁移脚本
"""
import os
import sys
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接信息 - 根据App/__init__.py中的配置设置
DB_HOST = 'localhost'  
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '651748264Zz*'  # 从App/__init__.py中取得的密码
DB_NAME = 'travelindustry'  # 从App/__init__.py中取得的数据库名

def execute_sql_file(filename):
    """执行SQL文件"""
    try:
        # 打开并读取SQL文件
        with open(filename, 'r', encoding='utf-8') as file:
            sql_commands = file.read()
        
        # 连接数据库
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        
        try:
            # 创建游标
            with connection.cursor() as cursor:
                # 执行SQL命令
                for command in sql_commands.split(';'):
                    command = command.strip()
                    if command:
                        print(f"执行: {command}")
                        cursor.execute(command)
                
                # 提交事务
                connection.commit()
                print(f"成功执行SQL文件: {filename}")
        finally:
            connection.close()
    except Exception as e:
        print(f"执行SQL文件时出错: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # 获取要执行的SQL文件名
    if len(sys.argv) > 1:
        sql_file = sys.argv[1]
    else:
        sql_file = "add_passenger_fields.sql"
    
    # 构建完整路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(script_dir, sql_file)
    
    # 执行SQL文件
    if os.path.exists(sql_path):
        success = execute_sql_file(sql_path)
        if success:
            print("迁移成功完成")
        else:
            print("迁移失败")
    else:
        print(f"SQL文件不存在: {sql_path}") 