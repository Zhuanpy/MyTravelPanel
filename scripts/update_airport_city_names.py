# -*- coding: utf-8 -*-
"""
批量更新机场城市英文名
运行方式：python scripts/update_airport_city_names.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.models import AirportData

# 常用机场城市英文名映射
CITY_NAMES_EN = {
    # 新加坡
    'SIN': 'Singapore',

    # 中国大陆
    'PEK': 'Beijing', 'PKX': 'Beijing',
    'PVG': 'Shanghai', 'SHA': 'Shanghai',
    'CAN': 'Guangzhou', 'SZX': 'Shenzhen',
    'CTU': 'Chengdu', 'TFU': 'Chengdu',
    'CKG': 'Chongqing', 'WUH': 'Wuhan',
    'XIY': 'Xian', 'HGH': 'Hangzhou',
    'NKG': 'Nanjing', 'KMG': 'Kunming',
    'XMN': 'Xiamen', 'TAO': 'Qingdao',
    'DLC': 'Dalian', 'TSN': 'Tianjin',
    'SHE': 'Shenyang', 'CSX': 'Changsha',
    'CGO': 'Zhengzhou', 'HAK': 'Haikou',
    'SYX': 'Sanya', 'FOC': 'Fuzhou',
    'NNG': 'Nanning', 'KWE': 'Guiyang',
    'LXA': 'Lhasa', 'URC': 'Urumqi',
    'HRB': 'Harbin', 'CGQ': 'Changchun',
    'TNA': 'Jinan', 'SJW': 'Shijiazhuang',
    'TYN': 'Taiyuan', 'HET': 'Hohhot',
    'INC': 'Yinchuan', 'LHW': 'Lanzhou',
    'XNN': 'Xining', 'ZUH': 'Zhuhai',
    'SWA': 'Shantou', 'WNZ': 'Wenzhou',
    'NGB': 'Ningbo', 'YNT': 'Yantai',
    'WUX': 'Wuxi', 'HFE': 'Hefei',
    'KHN': 'Nanchang', 'LYA': 'Luoyang',

    # 港澳台
    'HKG': 'Hong Kong',
    'MFM': 'Macau',
    'TPE': 'Taipei', 'TSA': 'Taipei',
    'KHH': 'Kaohsiung', 'RMQ': 'Taichung',

    # 日本
    'NRT': 'Tokyo', 'HND': 'Tokyo',
    'KIX': 'Osaka', 'ITM': 'Osaka',
    'NGO': 'Nagoya', 'CTS': 'Sapporo',
    'FUK': 'Fukuoka', 'OKA': 'Okinawa',

    # 韩国
    'ICN': 'Seoul', 'GMP': 'Seoul',
    'PUS': 'Busan', 'CJU': 'Jeju',

    # 东南亚
    'KUL': 'Kuala Lumpur', 'PEN': 'Penang',
    'BKI': 'Kota Kinabalu', 'KCH': 'Kuching',
    'LGK': 'Langkawi', 'JHB': 'Johor Bahru',
    'BKK': 'Bangkok', 'DMK': 'Bangkok',
    'CNX': 'Chiang Mai', 'HKT': 'Phuket',
    'USM': 'Koh Samui', 'KBV': 'Krabi',
    'SGN': 'Ho Chi Minh', 'HAN': 'Hanoi',
    'DAD': 'Da Nang', 'CXR': 'Nha Trang',
    'PQC': 'Phu Quoc',
    'MNL': 'Manila', 'CEB': 'Cebu',
    'CGK': 'Jakarta', 'DPS': 'Bali',
    'SUB': 'Surabaya', 'JOG': 'Yogyakarta',
    'RGN': 'Yangon', 'MDL': 'Mandalay',
    'REP': 'Siem Reap', 'PNH': 'Phnom Penh',
    'VTE': 'Vientiane', 'LPQ': 'Luang Prabang',
    'BWN': 'Bandar Seri Begawan',

    # 南亚
    'DEL': 'Delhi', 'BOM': 'Mumbai',
    'MAA': 'Chennai', 'BLR': 'Bangalore',
    'CCU': 'Kolkata', 'HYD': 'Hyderabad',
    'CMB': 'Colombo', 'MLE': 'Male',
    'KTM': 'Kathmandu', 'DAC': 'Dhaka',
    'KHI': 'Karachi', 'ISB': 'Islamabad',

    # 中东
    'DXB': 'Dubai', 'AUH': 'Abu Dhabi',
    'DOH': 'Doha', 'BAH': 'Bahrain',
    'KWI': 'Kuwait', 'MCT': 'Muscat',
    'RUH': 'Riyadh', 'JED': 'Jeddah',
    'TLV': 'Tel Aviv', 'AMM': 'Amman',
    'BEY': 'Beirut', 'CAI': 'Cairo',
    'IST': 'Istanbul', 'ESB': 'Ankara',

    # 澳洲/新西兰
    'SYD': 'Sydney', 'MEL': 'Melbourne',
    'BNE': 'Brisbane', 'PER': 'Perth',
    'ADL': 'Adelaide', 'CNS': 'Cairns',
    'OOL': 'Gold Coast',
    'AKL': 'Auckland', 'CHC': 'Christchurch',
    'WLG': 'Wellington', 'ZQN': 'Queenstown',

    # 北美
    'LAX': 'Los Angeles', 'SFO': 'San Francisco',
    'JFK': 'New York', 'EWR': 'New York',
    'LGA': 'New York', 'ORD': 'Chicago',
    'DFW': 'Dallas', 'ATL': 'Atlanta',
    'MIA': 'Miami', 'SEA': 'Seattle',
    'BOS': 'Boston', 'DEN': 'Denver',
    'LAS': 'Las Vegas', 'PHX': 'Phoenix',
    'IAD': 'Washington', 'DCA': 'Washington',
    'HNL': 'Honolulu', 'YVR': 'Vancouver',
    'YYZ': 'Toronto', 'YUL': 'Montreal',
    'MEX': 'Mexico City', 'CUN': 'Cancun',

    # 欧洲
    'LHR': 'London', 'LGW': 'London',
    'STN': 'London', 'LTN': 'London',
    'CDG': 'Paris', 'ORY': 'Paris',
    'FRA': 'Frankfurt', 'MUC': 'Munich',
    'AMS': 'Amsterdam', 'BRU': 'Brussels',
    'ZRH': 'Zurich', 'GVA': 'Geneva',
    'VIE': 'Vienna', 'PRG': 'Prague',
    'WAW': 'Warsaw', 'BUD': 'Budapest',
    'FCO': 'Rome', 'MXP': 'Milan',
    'VCE': 'Venice', 'MAD': 'Madrid',
    'BCN': 'Barcelona', 'LIS': 'Lisbon',
    'ATH': 'Athens', 'CPH': 'Copenhagen',
    'ARN': 'Stockholm', 'OSL': 'Oslo',
    'HEL': 'Helsinki', 'DUB': 'Dublin',
    'EDI': 'Edinburgh', 'MAN': 'Manchester',
    'SVO': 'Moscow', 'LED': 'St Petersburg',

    # 非洲
    'JNB': 'Johannesburg', 'CPT': 'Cape Town',
    'NBO': 'Nairobi', 'ADD': 'Addis Ababa',
    'CMN': 'Casablanca', 'ALG': 'Algiers',
    'LOS': 'Lagos', 'ACC': 'Accra',

    # 南美
    'GRU': 'Sao Paulo', 'GIG': 'Rio de Janeiro',
    'EZE': 'Buenos Aires', 'SCL': 'Santiago',
    'LIM': 'Lima', 'BOG': 'Bogota',
}

app = create_app()

with app.app_context():
    updated = 0
    not_found = []

    for iata, city_en in CITY_NAMES_EN.items():
        airport = AirportData.query.filter_by(airport_IATA=iata).first()
        if airport:
            airport.city_name_en = city_en
            updated += 1
        else:
            not_found.append(iata)

    db.session.commit()

    print(f"成功更新 {updated} 个机场的城市英文名")
    if not_found:
        print(f"以下机场代码在数据库中不存在: {', '.join(not_found)}")
