import requests
from typing import Dict, Optional, List
import json
import time
import os
from datetime import datetime
import sqlite3
import re

class FlightDB:
    def __init__(self, db_path="flights.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_number TEXT NOT NULL,
                airline TEXT NOT NULL,
                airline_num TEXT NOT NULL,
                schedule_city TEXT NOT NULL,
                schedule_timing TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_flight(self, flight_number: str) -> Optional[Dict]:
        """从数据库获取航班信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM flights WHERE flight_number = ? ORDER BY created_at DESC LIMIT 1",
            (flight_number,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'flight_number': row[1],
                'airline': row[2],
                'airline_num': row[3],
                'schedule_city': row[4],
                'schedule_timing': row[5],
                'created_at': row[6]
            }
        return None

    def save_flight(self, flight_data: Dict) -> bool:
        """保存航班信息到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO flights (flight_number, airline, airline_num, schedule_city, schedule_timing)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                flight_data['flight_number'],
                flight_data['airline'],
                flight_data['airline_num'],
                flight_data['schedule_city'],
                flight_data['schedule_timing']
            ))
            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"保存数据时出错: {e}")
            return False

class FlightScraper:
    def __init__(self, db: FlightDB):
        self.db = db
        # 初始化 API keys 列表
        self.api_keys = [
            '11616410fa3787c227f606509ad76108'  # 直接使用 API key
        ]
        
        if not self.api_keys:
            raise ValueError("No API keys found. Please set at least one AVIATIONSTACK_API_KEY")
        
        self.current_key_index = 0
        self.base_url = "http://api.aviationstack.com/v1/flights"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }

    def _get_current_api_key(self) -> str:
        """获取当前使用的 API key"""
        return self.api_keys[self.current_key_index]

    def _switch_to_next_api_key(self) -> bool:
        """切换到下一个可用的 API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"\n切换到 API key {self.current_key_index + 1}")
        return True

    def parse_flight_number(self, flight_number: str) -> tuple:
        """解析航班号为航司代码和航班编号"""
        flight_number = flight_number.strip().upper()
        if not flight_number:
            raise ValueError("航班号不能为空")
        
        # 使用正则表达式分离航司代码和航班编号
        match = re.match(r'^([A-Z]{2})(\d+)$', flight_number.replace(' ', ''))
        if not match:
            raise ValueError("航班号格式无效，请使用如 'MU714' 的格式")
        
        airline, number = match.groups()
        return airline, number

    def input_flight_details(self) -> Dict[str, str]:
        """输入航班详细信息"""
        while True:
            try:
                # 输入出发城市和到达城市
                dep_city = input("请输入出发城市代码 (例如: PEK): ").strip().upper()
                arr_city = input("请输入到达城市代码 (例如: SHA): ").strip().upper()
                if not dep_city or not arr_city:
                    raise ValueError("城市代码不能为空")
                if not re.match(r'^[A-Z]{3}$', dep_city) or not re.match(r'^[A-Z]{3}$', arr_city):
                    raise ValueError("城市代码必须是3个字母")

                # 输入起飞和到达时间
                dep_time = input("请输入起飞时间 (格式 HHMM，例如: 1430): ").strip()
                arr_time = input("请输入到达时间 (格式 HHMM，例如: 1630): ").strip()
                if not re.match(r'^\d{4}$', dep_time) or not re.match(r'^\d{4}$', arr_time):
                    raise ValueError("时间格式必须是4位数字(HHMM)")

                # 验证时间格式
                hours_dep, minutes_dep = int(dep_time[:2]), int(dep_time[2:])
                hours_arr, minutes_arr = int(arr_time[:2]), int(arr_time[2:])
                if hours_dep > 23 or minutes_dep > 59 or hours_arr > 23 or minutes_arr > 59:
                    raise ValueError("无效的时间格式")

                return {
                    'schedule_city': f"{dep_city}-{arr_city}",
                    'schedule_timing': f"{dep_time}-{arr_time}"
                }
            except ValueError as e:
                print(f"输入错误: {e}")
                print("请重新输入\n")

    def get_flight_info(self, flight_number: str) -> Optional[Dict]:
        """获取航班信息"""
        try:
            # 首先检查数据库
            print(f"\n正在查询航班 {flight_number} 的信息...")
            db_flight = self.db.get_flight(flight_number)
            if db_flight:
                print("从数据库找到航班信息")
                return db_flight

            # 解析航班号
            airline, number = self.parse_flight_number(flight_number)
            
            # 获取用户输入的航班详细信息
            print("\n请输入航班详细信息：")
            flight_details = self.input_flight_details()
            
            # 构造航班信息
            flight_data = {
                'flight_number': flight_number,
                'airline': airline,
                'airline_num': number,
                'schedule_city': flight_details['schedule_city'],
                'schedule_timing': flight_details['schedule_timing']
            }

            # 保存到数据库
            if self.db.save_flight(flight_data):
                print("航班信息已保存到数据库")
                return flight_data
            else:
                print("保存航班信息失败")
                return None

        except Exception as e:
            print(f"处理数据时出错: {e}")
            print(f"错误类型: {type(e).__name__}")
            return None

def main():
    try:
        db = FlightDB()
        scraper = FlightScraper(db)
        print("成功初始化航班查询系统")
    except Exception as e:
        print(f"初始化错误: {e}")
        return

    while True:
        try:
            flight_number = input("\n请输入航班号 (例如: MU714) 或输入 'q' 退出: ")
            if flight_number.lower() == 'q':
                break
                
            flight_info = scraper.get_flight_info(flight_number)
            if flight_info:
                print("\n航班信息:")
                print(json.dumps(flight_info, indent=2, ensure_ascii=False))
            
            # 添加延迟以避免频繁请求
            time.sleep(1)
            
        except ValueError as e:
            print(f"输入错误: {e}")
        except KeyboardInterrupt:
            print("\n程序已退出")
            break

if __name__ == "__main__":
    main() 