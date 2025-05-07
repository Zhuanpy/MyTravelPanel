import requests
from typing import Dict, Optional, List, Tuple
import json
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup

"""
FlightRadar24 航班数据抓取模块

本模块提供从FlightRadar24网站抓取航班信息的功能，支持通过航班号检索航班的各种信息。

主要功能:
1. 根据航班号获取航班详细信息 (起飞时间、到达时间、航线等)
2. 解析HTML表格提取航班数据
3. 处理时间戳与时区转换
4. 提供多重备用方案确保数据可靠性

技术说明:
- 使用BeautifulSoup解析HTML内容
- 支持时间戳与时区转换
- 多种数据提取策略，确保信息准确性
- 支持提取标准起飞时间(STD)、实际起飞时间(ATD)、标准到达时间(STA)等关键指标
- 对表格结构和标签变化有适应性处理

使用示例:
```python
from code.utils.flightradar24 import search_flight

# 获取航班MU544的信息
flight_info = search_flight('MU544')
print(flight_info)
```

注意事项:
- 由于网站结构可能发生变化，抓取逻辑可能需要定期更新
- 时区转换基于网站提供的data-offset属性进行处理
- 对于未起飞的航班，ATD（实际起飞时间）可能显示为"Unknown"
- 如果FlightRadar24无法获取数据，可以配置回退至其他数据源

"""

# 修改时间戳转换函数，支持时区偏移
def convert_timestamp_to_time(timestamp_str: str, offset_str: str = None) -> str:
    """将Unix时间戳转换为HH:MM格式的时间，考虑时区偏移"""
    try:
        # 转换为整数时间戳
        timestamp = int(timestamp_str)
        
        # 处理时区偏移 (如果有)
        offset_seconds = 0
        if offset_str and offset_str.isdigit():
            offset_seconds = int(offset_str)
            print(f"应用时区偏移: {offset_seconds} 秒 ({offset_seconds/3600} 小时)")
        
        # 转换为datetime对象 (使用UTC)
        dt_utc = datetime.utcfromtimestamp(timestamp)
        
        # 应用时区偏移
        if offset_seconds:
            dt = dt_utc + timedelta(seconds=offset_seconds)
        else:
            dt = dt_utc
            
        # 格式化为HH:MM
        time_str = dt.strftime('%H:%M')
        print(f"时间戳 {timestamp_str} 转换结果: {time_str}")
        return time_str
    except (ValueError, TypeError) as e:
        print(f"时间戳转换错误: {e}")
        return "Unknown"

def parse_flight_number(flight_number: str) -> Tuple[str, str]:
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

def get_flight_from_flightradar24(flight_number: str) -> Optional[Dict]:
    """从FlightRadar24网站抓取航班信息"""
    try:
        print(f"\n正在从FlightRadar24获取航班 {flight_number} 的信息...")
        
        # 构建URL - 替换航班号
        url = f"https://www.flightradar24.com/data/flights/{flight_number.lower()}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 打印网页标题，确认我们获取了正确的页面
        print(f"页面标题: {soup.title.text.strip()}")
        
        # 尝试多种方法查找航班信息表格
        flight_table = None
        
        # 方法1: 尝试使用class='table'查找
        tables_with_class = soup.find_all('table', class_='table')
        if tables_with_class:
            print(f"找到 {len(tables_with_class)} 个class='table'的表格")
            flight_table = tables_with_class[0]
        
        # 方法2: 尝试查找所有表格，并找出包含航班信息的表格
        if not flight_table:
            all_tables = soup.find_all('table')
            print(f"找到总共 {len(all_tables)} 个表格")
            
            for i, table in enumerate(all_tables):
                # 打印表格的前20个字符，帮助调试
                table_text = table.get_text().strip().replace('\n', ' ')[:50]
                print(f"表格 {i+1}: {table_text}...")
                
                # 查找包含航班信息的表格 (通常包含"Flight"、"From"、"To"等关键词)
                if any(keyword in table_text for keyword in ['Flight', 'From', 'To', 'DATE', 'AIRCRAFT']):
                    print(f"表格 {i+1} 可能包含航班信息")
                    flight_table = table
                    break
        
        # 如果仍然找不到表格，尝试直接从页面提取信息
        if not flight_table:
            print("无法找到航班历史表格，尝试从页面提取基本信息")
            
            # 尝试查找特定航班信息区域
            flight_section = soup.find('div', {'id': 'cnt-data-content'}) or soup.find('div', {'class': 'flight-info-panel'})
            
            if flight_section:
                print("找到航班信息区域")
                # 尝试查找起飞/到达信息
                return extract_flightradar_detailed_info(soup, flight_number)
            else:
                return extract_flightradar_basic_info(soup, flight_number)
        
        # 获取表格行
        rows = flight_table.find_all('tr')
        
        # 如果表格太小，无法提取信息
        if len(rows) < 2:
            print("表格中没有足够的行")
            return extract_flightradar_basic_info(soup, flight_number)
        
        # 输出表头，帮助我们理解表格结构
        if len(rows) > 0:
            header_cells = rows[0].find_all(['th', 'td'])
            headers = [cell.get_text().strip() for cell in header_cells]
            print(f"表头: {headers}")
        
        # 提取所有航班数据
        flight_records = []
        for i, row in enumerate(rows[1:]):  # 跳过表头行
            if 'data-row' in row.get('class', []) or row.find('td'):
                flight_data = extract_flight_data_from_row(row, flight_number)
                if flight_data:
                    flight_records.append(flight_data)
                    print(f"提取到第 {i+1} 个航班记录")
        
        if flight_records:
            print(f"成功从FlightRadar24提取到 {len(flight_records)} 个航班记录")
            # 返回第一个记录作为当前航班信息
            return flight_records[0]
        else:
            print("无法从表格行提取数据，尝试基本信息提取")
            return extract_flightradar_basic_info(soup, flight_number)
    
    except requests.RequestException as e:
        print(f"FlightRadar24请求错误: {e}")
        return None
    except Exception as e:
        print(f"处理FlightRadar24数据时出错: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def extract_flight_data_from_row(row, flight_number: str) -> Optional[Dict]:
    """从表格行中提取航班数据"""
    try:
        # 打印行内容，帮助调试
        row_text = row.get_text().strip().replace('\n', ' ')[:100]
        print(f"提取数据行: {row_text}...")
        
        # 初始化航班数据字典
        flight_info = {
            'date': "Unknown",
            'from_airport': "Unknown",
            'from_iata': "Unknown",
            'to_airport': "Unknown",
            'to_iata': "Unknown",
            'aircraft': "Unknown",
            'flight_time': "Unknown",
            'std': "Unknown",  # 计划起飞时间
            'atd': "Unknown",  # 实际起飞时间
            'sta': "Unknown",  # 计划到达时间
            'status': "Unknown"
        }
        
        # 1. 提取基本数据 (机场、飞机型号等)
        
        # 尝试获取日期 - 查找带有data-timestamp属性的元素
        date_elem = row.find(attrs={'data-time-format': 'DD MMM YYYY'})
        if date_elem:
            flight_info['date'] = date_elem.get_text().strip()
        
        # 尝试查找出发机场 (SIN)
        from_elem = row.find('label', string='FROM')
        if from_elem and from_elem.find_next():
            from_airport_text = from_elem.find_next().get_text().strip()
            flight_info['from_airport'] = from_airport_text
            # 提取IATA代码
            from_iata_match = re.search(r'\(([A-Z]{3})\)', from_airport_text)
            if from_iata_match:
                flight_info['from_iata'] = from_iata_match.group(1)
        
        # 尝试查找到达机场 (PVG)
        to_elem = row.find('label', string='TO')
        if to_elem and to_elem.find_next():
            to_airport_text = to_elem.find_next().get_text().strip()
            flight_info['to_airport'] = to_airport_text
            # 提取IATA代码
            to_iata_match = re.search(r'\(([A-Z]{3})\)', to_airport_text)
            if to_iata_match:
                flight_info['to_iata'] = to_iata_match.group(1)
        
        # 尝试获取飞机类型
        aircraft_cells = row.find_all('td')
        for cell in aircraft_cells:
            cell_text = cell.get_text().strip()
            # 飞机类型通常是短代码，如 77W, 320, 788 等
            if re.match(r'^[A-Z0-9]{3,4}$', cell_text):
                flight_info['aircraft'] = cell_text
                break
        
        # 2. 直接从标签和时间戳中提取时间数据
        print("\n=== 从详细标签元素提取时间信息 ===")
        
        # STD - 计划起飞时间
        std_span = row.find('label', string='STD').find_next('span', class_='details') if row.find('label', string='STD') else None
        if std_span:
            print(f"找到STD元素: {std_span}")
            # 首选: 检查时间戳
            timestamp = std_span.get('data-timestamp')
            offset = std_span.get('data-offset')
            if timestamp and timestamp.isdigit():
                # 从时间戳转换
                flight_info['std'] = convert_timestamp_to_time(timestamp, offset)
                print(f"从时间戳提取STD: {flight_info['std']}")
            else:
                # 备选: 从文本提取
                std_text = std_span.get_text().strip()
                if std_text and std_text != "—":
                    flight_info['std'] = std_text
                    print(f"从文本提取STD: {flight_info['std']}")
        
        # ATD - 实际起飞时间
        atd_span = row.find('label', string='ATD').find_next('span', class_='details') if row.find('label', string='ATD') else None
        if atd_span:
            print(f"找到ATD元素: {atd_span}")
            # 首选: 检查时间戳
            timestamp = atd_span.get('data-timestamp')
            offset = atd_span.get('data-offset')
            if timestamp and timestamp.isdigit():
                # 从时间戳转换
                flight_info['atd'] = convert_timestamp_to_time(timestamp, offset)
                print(f"从时间戳提取ATD: {flight_info['atd']}")
            else:
                # 备选: 从文本提取
                atd_text = atd_span.get_text().strip()
                if atd_text and atd_text != "—":
                    flight_info['atd'] = atd_text
                    print(f"从文本提取ATD: {flight_info['atd']}")
        
        # STA - 计划到达时间
        sta_span = row.find('label', string='STA').find_next('span', class_='details') if row.find('label', string='STA') else None
        if sta_span:
            print(f"找到STA元素: {sta_span}")
            # 首选: 检查时间戳
            timestamp = sta_span.get('data-timestamp')
            offset = sta_span.get('data-offset')
            if timestamp and timestamp.isdigit():
                # 从时间戳转换
                flight_info['sta'] = convert_timestamp_to_time(timestamp, offset)
                print(f"从时间戳提取STA: {flight_info['sta']}")
            else:
                # 备选: 从文本提取
                sta_text = sta_span.get_text().strip()
                if sta_text and sta_text != "—":
                    flight_info['sta'] = sta_text
                    print(f"从文本提取STA: {flight_info['sta']}")
        
        # 3. 如果上面方法失败，尝试从其他位置查找 (备用方案)
        print("\n=== 备用时间提取方法 ===")
        
        # 尝试寻找隐藏的td元素
        if flight_info['std'] == "Unknown" or flight_info['sta'] == "Unknown":
            # 查找包含时间戳的td元素
            std_td = row.find('td', attrs={'data-timestamp': True, 'class': 'hidden-xs hidden-sm'})
            if std_td:
                siblings = list(std_td.find_next_siblings('td', attrs={'data-timestamp': True}))
                
                # 打印调试信息
                print(f"找到 {len(siblings) + 1} 个带时间戳的td元素")
                for i, td in enumerate([std_td] + siblings):
                    ts = td.get('data-timestamp')
                    offset = td.get('data-offset')
                    print(f"时间戳TD[{i}]: ts={ts}, offset={offset}, 文本='{td.get_text().strip()}'")
                
                # 通常STD, ATD, STA按顺序排列
                if flight_info['std'] == "Unknown" and std_td.get('data-timestamp'):
                    flight_info['std'] = convert_timestamp_to_time(std_td.get('data-timestamp'), std_td.get('data-offset'))
                    print(f"从td提取STD: {flight_info['std']}")
                
                # ATD通常是第二个时间戳元素
                if flight_info['atd'] == "Unknown" and len(siblings) >= 1:
                    atd_td = siblings[0]
                    if atd_td.get('data-timestamp'):
                        flight_info['atd'] = convert_timestamp_to_time(atd_td.get('data-timestamp'), atd_td.get('data-offset'))
                        print(f"从td提取ATD: {flight_info['atd']}")
                
                # STA通常是第三个时间戳元素
                if flight_info['sta'] == "Unknown" and len(siblings) >= 2:
                    sta_td = siblings[1]
                    if sta_td.get('data-timestamp'):
                        flight_info['sta'] = convert_timestamp_to_time(sta_td.get('data-timestamp'), sta_td.get('data-offset'))
                        print(f"从td提取STA: {flight_info['sta']}")
        
        # 4. 最后的备用方案 - 直接在行内提取所有时间
        if flight_info['std'] == "Unknown" or flight_info['atd'] == "Unknown" or flight_info['sta'] == "Unknown":
            print("使用最终备用方案 - 提取所有时间文本")
            all_times = re.findall(r'\d{2}:\d{2}', row.get_text())
            print(f"提取到 {len(all_times)} 个时间: {all_times}")
            
            # 按照常见顺序分配
            if all_times:
                if flight_info['std'] == "Unknown" and len(all_times) > 0:
                    flight_info['std'] = all_times[0]
                
                if flight_info['atd'] == "Unknown" and len(all_times) > 1:
                    flight_info['atd'] = all_times[1]
                
                if flight_info['sta'] == "Unknown" and len(all_times) > 2:
                    flight_info['sta'] = all_times[2]
        
        # 提取航班状态
        status_elem = row.find(attrs={'data-prefix': 'Scheduled '})
        if status_elem:
            flight_info['status'] = status_elem.get_text().strip()
        
        # 最终输出提取的时间数据，便于调试
        print(f"\n最终提取的航班时间信息:")
        print(f"  STD(计划起飞时间): {flight_info['std']}")
        print(f"  ATD(实际起飞时间): {flight_info['atd']}")
        print(f"  STA(计划到达时间): {flight_info['sta']}")
        
        # 构建返回数据格式 (与API格式兼容)
        airline, flight_num = parse_flight_number(flight_number)
        
        result = {
            'data': [{
                'flight': {
                    'iata': flight_number
                },
                'departure': {
                    'iata': flight_info['from_iata'],
                    'scheduled': flight_info['std']
                },
                'arrival': {
                    'iata': flight_info['to_iata'],
                    'scheduled': flight_info['sta']
                },
                'airline': {
                    'name': get_airline_name(airline)
                },
                'flight_date': flight_info['date'],
                'status': flight_info['status'],
                'aircraft': flight_info['aircraft'],
                # 保存原始详细数据，以便需要时使用
                'raw_data': flight_info
            }]
        }
        
        return result
    
    except Exception as e:
        print(f"从表格行提取数据时出错: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def extract_flightradar_detailed_info(soup, flight_number: str) -> Optional[Dict]:
    """从FlightRadar24页面中提取详细航班信息"""
    try:
        print("尝试提取详细航班信息...")
        
        # 初始化变量
        from_iata = "Unknown"
        to_iata = "Unknown"
        scheduled_departure = "Unknown"
        scheduled_arrival = "Unknown"
        
        # 尝试提取航班信息
        
        # 1. 查找包含机场代码的元素
        airport_elements = soup.find_all(['div', 'span', 'p', 'h1', 'h2', 'h3'], text=re.compile(r'\([A-Z]{3}\)'))
        print(f"找到 {len(airport_elements)} 个包含机场代码的元素")
        
        # 提取前两个机场代码 (通常是出发地和目的地)
        airport_codes = []
        for elem in airport_elements:
            matches = re.findall(r'\(([A-Z]{3})\)', elem.text)
            airport_codes.extend(matches)
        
        if len(airport_codes) >= 2:
            from_iata = airport_codes[0]
            to_iata = airport_codes[1]
            print(f"找到机场代码: {from_iata} -> {to_iata}")
        
        # 2. 查找包含时间的元素 (格式通常是 HH:MM)
        time_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'\d{2}:\d{2}'))
        print(f"找到 {len(time_elements)} 个包含时间的元素")
        
        # 提取前两个时间 (通常是出发时间和到达时间)
        times = []
        for elem in time_elements:
            matches = re.findall(r'(\d{2}:\d{2})', elem.text)
            times.extend(matches)
        
        if len(times) >= 2:
            scheduled_departure = times[0]
            scheduled_arrival = times[1]
            print(f"找到时间: {scheduled_departure} -> {scheduled_arrival}")
        
        # 3. 尝试查找航线信息 (备用方法)
        route_info = soup.find('h1', class_='subTitle') or soup.find('div', class_='route-info')
        if route_info:
            route_text = route_info.text.strip()
            print(f"找到路线信息: {route_text}")
            
            # 尝试提取机场代码
            if from_iata == "Unknown" or to_iata == "Unknown":
                airports = re.findall(r'\(([A-Z]{3})\)', route_text)
                if len(airports) >= 2:
                    from_iata = airports[0]
                    to_iata = airports[1]
        
        # 构建结果
        airline, flight_num = parse_flight_number(flight_number)
        
        result = {
            'data': [{
                'flight': {
                    'iata': flight_number
                },
                'departure': {
                    'iata': from_iata,
                    'scheduled': scheduled_departure
                },
                'arrival': {
                    'iata': to_iata,
                    'scheduled': scheduled_arrival
                },
                'airline': {
                    'name': get_airline_name(airline)
                }
            }]
        }
        
        return result
    
    except Exception as e:
        print(f"提取详细信息时出错: {e}")
        return None

def extract_flightradar_basic_info(soup, flight_number: str) -> Optional[Dict]:
    """从页面中提取基本航班信息"""
    try:
        # 尝试找到航班路线信息
        route_info = soup.find('h1', class_='subTitle')
        if route_info:
            route_text = route_info.text.strip()
            print(f"找到路线信息: {route_text}")
            
            # 尝试从路线文本中提取机场代码
            airports = re.findall(r'\(([A-Z]{3})\)', route_text)
            
            if len(airports) >= 2:
                from_iata = airports[0]
                to_iata = airports[1]
                
                # 构建基本结果
                airline, flight_num = parse_flight_number(flight_number)
                
                result = {
                    'data': [{
                        'flight': {
                            'iata': flight_number
                        },
                        'departure': {
                            'iata': from_iata,
                            'scheduled': "Unknown"
                        },
                        'arrival': {
                            'iata': to_iata,
                            'scheduled': "Unknown"
                        },
                        'airline': {
                            'name': get_airline_name(airline)
                        }
                    }]
                }
                
                return result
        
        # 如果找不到路线信息，构建一个最基本的响应
        airline, flight_num = parse_flight_number(flight_number)
        
        result = {
            'data': [{
                'flight': {
                    'iata': flight_number
                },
                'departure': {
                    'iata': "Unknown",
                    'scheduled': "Unknown"
                },
                'arrival': {
                    'iata': "Unknown",
                    'scheduled': "Unknown"
                },
                'airline': {
                    'name': get_airline_name(airline)
                }
            }]
        }
        
        return result
    
    except Exception as e:
        print(f"提取基本信息时出错: {e}")
        return None

def get_airline_name(airline_code: str) -> str:
    """根据航空公司代码获取航空公司名称"""
    airlines = {
        'MU': '中国东方航空',
        'CZ': '中国南方航空',
        'CA': '中国国际航空',
        'ZH': '深圳航空',
        'HU': '海南航空',
        'MF': '厦门航空',
        '3U': '四川航空',
        '9C': '春秋航空',
        'FM': '上海航空',
        'JD': '首都航空',
        'HO': '吉祥航空',
        'NS': '河北航空',
        'AK': '亚洲航空',
        'SQ': '新加坡航空',
        'CX': '国泰航空',
        'NH': '全日空航空',
        'JL': '日本航空',
        'KE': '大韩航空',
        'TG': '泰国航空',
        'VN': '越南航空',
        'SU': '俄罗斯航空',
        'EK': '阿联酋航空',
        'QR': '卡塔尔航空',
        'LH': '汉莎航空',
        'AF': '法国航空',
        'BA': '英国航空',
        'UA': '美国联合航空',
        'AA': '美国航空',
        'DL': '达美航空'
    }
    
    return airlines.get(airline_code, f"Unknown Airline ({airline_code})")

def get_flight_from_aviationstack(flight_number: str, api_key: str = '11616410fa3787c227f606509ad76108') -> Optional[Dict]:
    """从Aviationstack API获取航班信息"""
    try:
        base_url = "http://api.aviationstack.com/v1/flights"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }

        print(f"\n正在从Aviationstack API获取航班 {flight_number} 的信息...")

        # 构建 API 请求参数
        params = {
            'access_key': api_key,
            'flight_iata': flight_number
        }

        # 发送请求
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()

        # 解析响应
        data = response.json()

        # 打印原始响应以便调试
        print("\nAviationstack API 响应:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # 检查是否有错误
        if 'error' in data:
            print(f"Aviationstack API 错误: {data['error'].get('message', '未知错误')}")
            return None

        # 检查是否有航班数据
        if not data.get('data') or len(data['data']) == 0:
            print(f"Aviationstack API未找到航班 {flight_number} 的信息")
            return None

        return data
    
    except requests.RequestException as e:
        print(f"Aviationstack API请求错误: {e}")
        return None
    
    except Exception as e:
        print(f"处理Aviationstack数据时出错: {e}")
        return None

def get_flight_from_opensky(flight_number: str) -> Optional[Dict]:
    """从OpenSky Network API获取航班信息"""
    try:
        # 解析航班号
        airline, number = parse_flight_number(flight_number)
        callsign = f"{airline}{number}".ljust(8)  # OpenSky使用8字符的callsign
        
        # 获取当前时间和一小时前的时间戳
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        begin = int(one_hour_ago.timestamp())
        end = int(now.timestamp())
        
        print(f"\n正在从OpenSky API获取航班 {flight_number} 的信息...")
        
        # OpenSky API URL
        url = f"https://opensky-network.org/api/flights/aircraft"
        
        # 构建参数
        params = {
            'begin': begin,
            'end': end
        }
        
        # 发送请求
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # 解析响应
        flights = response.json()
        
        print(f"\nOpenSky API 响应 (飞行总数: {len(flights)}):")
        
        # 查找匹配的航班
        matching_flights = []
        for flight in flights:
            if flight.get('callsign', '').strip() == callsign.strip():
                matching_flights.append(flight)
        
        if not matching_flights:
            print(f"OpenSky API未找到航班 {flight_number} 的信息")
            return None
        
        # 选择最新的航班
        latest_flight = max(matching_flights, key=lambda x: x.get('lastSeen', 0))
        print(f"找到航班: {json.dumps(latest_flight, indent=2)}")
        
        # 构建返回数据格式
        result = {
            'data': [{
                'flight': {
                    'iata': flight_number,
                    'icao': latest_flight.get('callsign', '').strip()
                },
                'departure': {
                    'iata': latest_flight.get('estDepartureAirport', 'Unknown')
                },
                'arrival': {
                    'iata': latest_flight.get('estArrivalAirport', 'Unknown')
                }
            }]
        }
        
        return result
    except requests.RequestException as e:
        print(f"OpenSky API请求错误: {e}")
        return None
    except Exception as e:
        print(f"处理OpenSky数据时出错: {e}")
        return None

def get_flight_from_web_scraping(flight_number: str) -> Optional[Dict]:
    """通过网页抓取获取航班信息 (备用方案)"""
    try:
        print(f"\n正在尝试从网页抓取航班 {flight_number} 的信息...")
        
        # 使用Google搜索航班号
        search_url = f"https://www.google.com/search?q=flight+{flight_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        # 这里应该有更复杂的解析逻辑，但为简单起见，我们只返回一个基本结构
        # 实际项目中需要使用BeautifulSoup等工具进行解析
        
        # 由于抓取复杂度较高，这里只返回一个占位结果
        airline, number = parse_flight_number(flight_number)
        
        result = {
            'data': [{
                'flight': {
                    'iata': flight_number
                },
                'departure': {
                    'iata': 'XXX'  # 占位符
                },
                'arrival': {
                    'iata': 'YYY'  # 占位符
                }
            }]
        }
        
        print("网页抓取成功 (仅返回占位数据)")
        return result
        
    except Exception as e:
        print(f"网页抓取错误: {e}")
        return None

def extract_flight_data(data: Dict, flight_number: str) -> Optional[Dict]:
    """提取和格式化航班数据"""
    try:
        if not data.get('data') or len(data['data']) == 0:
            return None
            
        flight_data = data['data'][0]  # 获取第一个航班的数据
        
        # 提取 departure 信息
        departure = flight_data.get('departure', {})
        # departure_airport = departure.get('airport', 'Unknown')
        departure_iata = departure.get('iata', 'Unknown')
        departure_time = departure.get('scheduled', 'Unknown')
        
        # 提取 arrival 信息
        arrival = flight_data.get('arrival', {})
        # arrival_airport = arrival.get('airport', 'Unknown')
        arrival_iata = arrival.get('iata', 'Unknown')
        arrival_time = arrival.get('scheduled', 'Unknown')

        # 格式化时间
        formatted_dep_time = "Unknown"
        formatted_arr_time = "Unknown"
        
        try:
            if departure_time != 'Unknown' and ':' in departure_time:
                # 如果时间已经是HH:MM格式，直接使用
                formatted_dep_time = departure_time

            elif departure_time != 'Unknown':
                dep_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                formatted_dep_time = dep_datetime.strftime('%H:%M')
                print(f"\n格式化后的出发时间: {formatted_dep_time}")
            
            if arrival_time != 'Unknown' and ':' in arrival_time:
                # 如果时间已经是HH:MM格式，直接使用
                formatted_arr_time = arrival_time
            elif arrival_time != 'Unknown':
                arr_datetime = datetime.fromisoformat(arrival_time.replace('Z', '+00:00'))
                formatted_arr_time = arr_datetime.strftime('%H:%M')
                print(f"格式化后的到达时间: {formatted_arr_time}")
                
        except Exception as e:
            print(f"时间格式化错误: {e}")
        
        # 解析航班号
        airline, flight_num = parse_flight_number(flight_number)
        
        # 获取航空公司名称
        airline_name = flight_data.get('airline', {}).get('name', get_airline_name(airline))
        
        # 构建结果
        result = {
            'flight_number': flight_number,
            'airline': airline,
            'airline_num': flight_num,
            'airline_name': airline_name,
            'schedule_city': f"{departure_iata} {arrival_iata}",
            'schedule_timing': f"{formatted_dep_time} {formatted_arr_time}"
        }
        print(f"result: {result}")
        return result
    except Exception as e:
        print(f"提取数据时出错: {e}")
        return None

def search_flight(flight_number: str) -> Optional[Dict]:
    """搜索航班信息主函数 - 优先使用FlightRadar24"""
    try:
        # 验证航班号格式
        airline, number = parse_flight_number(flight_number)
        print(f"航空公司代码: {airline}, 航班编号: {number}")
        
        # 首先尝试 FlightRadar24
        # print("尝试从 FlightRadar24 获取数据...")
        flightradar_data = get_flight_from_flightradar24(flight_number)
        if flightradar_data and flightradar_data.get('data'):
            print("成功从 FlightRadar24 获取数据")
            return extract_flight_data(flightradar_data, flight_number)
        
        # 如果 FlightRadar24 失败，尝试 Aviationstack API
        print("FlightRadar24 获取失败，尝试 Aviationstack API...")
        api_data = get_flight_from_aviationstack(flight_number)
        if api_data and api_data.get('data') and len(api_data['data']) > 0:
            print("成功从 Aviationstack 获取数据")
            return extract_flight_data(api_data, flight_number)
        
        # 如果 Aviationstack 失败，尝试 OpenSky API
        print("Aviationstack 获取失败，尝试 OpenSky API...")
        opensky_data = get_flight_from_opensky(flight_number)
        if opensky_data and opensky_data.get('data'):
            print("成功从 OpenSky 获取数据")
            return extract_flight_data(opensky_data, flight_number)
        
        print("所有数据源都未能获取到航班信息")
        return None
    
    except ValueError as e:
        print(f"输入错误: {e}")
        return None
    except Exception as e:
        print(f"处理过程出错: {e}")
        return None

def get_all_flights_from_flightradar24(flight_number: str) -> List[Dict]:
    """获取航班的所有历史记录"""
    try:
        print(f"\n正在获取航班 {flight_number} 的所有历史记录...")
        
        # 构建URL - 替换航班号
        url = f"https://www.flightradar24.com/data/flights/{flight_number.lower()}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尝试多种方法查找航班信息表格
        flight_table = None
        
        # 方法1: 尝试使用class='table'查找
        tables_with_class = soup.find_all('table', class_='table')
        if tables_with_class:
            flight_table = tables_with_class[0]
        
        # 方法2: 尝试查找所有表格，并找出包含航班信息的表格
        if not flight_table:
            all_tables = soup.find_all('table')
            
            for table in all_tables:
                # 查找包含航班信息的表格 (通常包含"Flight"、"From"、"To"等关键词)
                table_text = table.get_text().strip().replace('\n', ' ')
                if any(keyword in table_text for keyword in ['Flight', 'From', 'To', 'DATE', 'AIRCRAFT']):
                    flight_table = table
                    break
        
        # 如果找不到表格，返回空列表
        if not flight_table:
            print("无法找到航班历史表格")
            return []
        
        # 获取表格行
        rows = flight_table.find_all('tr')
        
        # 如果表格太小，无法提取信息
        if len(rows) < 2:
            print("表格中没有足够的行")
            return []
        
        # 提取所有航班数据
        all_flights = []
        for i, row in enumerate(rows[1:]):  # 跳过表头行
            if 'data-row' in row.get('class', []) or row.find('td'):
                flight_data = extract_flight_data_from_row(row, flight_number)
                if flight_data and flight_data.get('data'):
                    all_flights.append(flight_data['data'][0])
                    print(f"添加第 {len(all_flights)} 个航班记录")
        
        print(f"总共提取到 {len(all_flights)} 个航班记录")
        return all_flights
    
    except Exception as e:
        print(f"获取所有航班记录时出错: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    flight_input = "AK5742"
    flight_info = search_flight(flight_input)


    