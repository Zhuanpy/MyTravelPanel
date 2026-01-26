# -*- coding: utf-8 -*-
"""
修复机票订单缺失数据

问题：部分机票REF没有对应的 ProjectFlightSegment/ProjectFlightPassenger 记录
数据来源：从 project_ref 表获取

修复思路：
1. 从 ProjectRef 表查找所有机票类型的REF（ref_type_id = 1）
2. 检查是否有对应的 ProjectFlightSegment 记录
3. 如果没有，从REF的description/extra_info解析航段并创建
4. 同时确保有 ProjectFlightPassenger 记录

数据表关系：
- ProjectRef -> ProjectFlightSegment (via ref_id)
- ProjectRef -> ProjectFlightPassenger (via ref_id)

注意：列表页 /flights_booking/orders 读取的是这些表，而不是 FlightOrder 表！
"""

import sys
import os
import re
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.project import ProjectHeader
from App_new.shared.models.business_types import BusinessType

app = create_app()


def parse_route_segments(detailed_description):
    """
    从详细描述中解析航段
    支持多种格式：
    - TAO/XMN/SIN/XMN/TAO (用/分隔)
    - SIN-PVG-SIN (用-分隔)
    - 25FEB NKG-SIN (日期+IATA代码)
    - NANJING-SIN (城市名转换为IATA代码)
    """
    if not detailed_description:
        return []

    text = detailed_description.upper()

    # 城市名到IATA代码的映射
    city_to_iata = {
        # 中国城市
        'NANJING': 'NKG', 'NANKING': 'NKG',
        'SHANGHAI': 'PVG', 'PUDONG': 'PVG', 'HONGQIAO': 'SHA',
        'BEIJING': 'PEK', 'PEKING': 'PEK', 'DAXING': 'PKX',
        'GUANGZHOU': 'CAN', 'CANTON': 'CAN',
        'SHENZHEN': 'SZX',
        'CHENGDU': 'CTU',
        'HANGZHOU': 'HGH',
        'XIAMEN': 'XMN', 'AMOY': 'XMN',
        'QINGDAO': 'TAO', 'TSINGTAO': 'TAO',
        'XIAN': 'XIY', "XI'AN": 'XIY',
        'KUNMING': 'KMG',
        'CHONGQING': 'CKG',
        'WUHAN': 'WUH',
        'TIANJIN': 'TSN',
        'DALIAN': 'DLC',
        'SANYA': 'SYX',
        'HAIKOU': 'HAK',
        'FUZHOU': 'FOC',
        'CHANGSHA': 'CSX',
        'ZHENGZHOU': 'CGO',
        'JINAN': 'TNA',
        'NANNING': 'NNG',
        'GUILIN': 'KWL',
        'HARBIN': 'HRB',
        'SHENYANG': 'SHE',
        'CHANGCHUN': 'CGQ',
        'URUMQI': 'URC',
        'LANZHOU': 'LHW',
        'HOHHOT': 'HET',
        'YINCHUAN': 'INC',
        'XINING': 'XNN',
        'LHASA': 'LXA',
        'GUIYANG': 'KWE',
        'TAIYUAN': 'TYN',
        'SHIJIAZHUANG': 'SJW',
        'HEFEI': 'HFE',
        'NANCHANG': 'KHN',
        'WENZHOU': 'WNZ',
        'NINGBO': 'NGB',
        'WUXI': 'WUX',
        'SUZHOU': 'SZV',
        'YANGZHOU': 'YTY',
        'ZHUHAI': 'ZUH',
        'MACAU': 'MFM', 'MACAO': 'MFM',
        # 港台
        'HONG KONG': 'HKG', 'HONGKONG': 'HKG',
        'TAIPEI': 'TPE', 'TAOYUAN': 'TPE',
        'KAOHSIUNG': 'KHH',
        # 东南亚
        'SINGAPORE': 'SIN',
        'BANGKOK': 'BKK', 'SUVARNABHUMI': 'BKK', 'DON MUEANG': 'DMK',
        'KUALA LUMPUR': 'KUL', 'KL': 'KUL',
        'JAKARTA': 'CGK',
        'BALI': 'DPS', 'DENPASAR': 'DPS',
        'MANILA': 'MNL',
        'HO CHI MINH': 'SGN', 'SAIGON': 'SGN',
        'HANOI': 'HAN',
        'PHNOM PENH': 'PNH',
        'YANGON': 'RGN',
        'PHUKET': 'HKT',
        'CHIANG MAI': 'CNX',
        # 日韩
        'TOKYO': 'NRT', 'NARITA': 'NRT', 'HANEDA': 'HND',
        'OSAKA': 'KIX', 'KANSAI': 'KIX',
        'SEOUL': 'ICN', 'INCHEON': 'ICN', 'GIMPO': 'GMP',
        'BUSAN': 'PUS',
        'JEJU': 'CJU',
        # 其他
        'SYDNEY': 'SYD',
        'MELBOURNE': 'MEL',
        'LONDON': 'LHR', 'HEATHROW': 'LHR', 'GATWICK': 'LGW',
        'PARIS': 'CDG',
        'NEW YORK': 'JFK', 'NYC': 'JFK',
        'LOS ANGELES': 'LAX', 'LA': 'LAX',
        'DUBAI': 'DXB',
    }

    # 先尝试将城市名替换为IATA代码
    processed_text = text
    for city, iata in sorted(city_to_iata.items(), key=lambda x: -len(x[0])):  # 先匹配长的
        processed_text = processed_text.replace(city, iata)

    # 模式1：匹配用 / 分隔的 IATA 代码
    pattern1 = r'([A-Z]{3}(?:/[A-Z]{3})+)'
    match1 = re.search(pattern1, processed_text)
    if match1:
        route_str = match1.group(1)
        airports = route_str.split('/')
        segments = []
        for i in range(len(airports) - 1):
            segments.append((airports[i], airports[i+1]))
        return segments

    # 模式2：匹配用 - 分隔的 IATA 代码（如 SIN-PVG-SIN 或 NKG-SIN）
    pattern2 = r'([A-Z]{3}(?:-[A-Z]{3})+)'
    match2 = re.search(pattern2, processed_text)
    if match2:
        route_str = match2.group(1)
        airports = route_str.split('-')
        segments = []
        for i in range(len(airports) - 1):
            segments.append((airports[i], airports[i+1]))
        return segments

    # 模式3：提取所有独立的 IATA 代码（3个大写字母，前后不是字母）
    iata_codes = re.findall(r'(?<![A-Z])([A-Z]{3})(?![A-Z])', processed_text)

    # 过滤掉非机场代码
    non_airport = {
        # 月份
        'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
        # 星期
        'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN',
        # 舱位/状态代码
        'HK', 'OK', 'RQ', 'HL', 'NN', 'UC', 'UN', 'US', 'TK', 'KK', 'KL',
        # 常见词
        'THE', 'AND', 'FOR', 'AIR', 'FLY', 'VIA',
        # 无效的3字母组合
        'ING', 'IAN', 'ANG', 'ENG', 'ONG', 'UNG',
    }
    iata_codes = [c for c in iata_codes if c not in non_airport]

    if len(iata_codes) >= 2:
        segments = []
        for i in range(len(iata_codes) - 1):
            segments.append((iata_codes[i], iata_codes[i+1]))
        return segments

    return []


def generate_flight_time(base_date, segment_index, is_morning=True):
    """
    生成航班时间
    """
    flight_date = base_date + timedelta(days=segment_index)

    if is_morning:
        dep_hour = random.randint(7, 10)
        dep_minute = random.choice([0, 15, 30, 45])
    else:
        dep_hour = random.randint(18, 21)
        dep_minute = random.choice([0, 15, 30, 45])

    departure_time = datetime(
        flight_date.year, flight_date.month, flight_date.day,
        dep_hour, dep_minute
    )

    flight_hours = random.randint(2, 5)
    flight_minutes = random.choice([0, 15, 30, 45])
    arrival_time = departure_time + timedelta(hours=flight_hours, minutes=flight_minutes)

    return departure_time, arrival_time


def get_route_description(ref):
    """
    获取航线描述，优先级：
    1. extra_info.flight_route
    2. description
    3. detailed_description
    """
    # 尝试从 extra_info 获取 flight_route
    if ref.extra_info:
        try:
            extra = json.loads(ref.extra_info)
            if extra.get('flight_route'):
                return extra['flight_route'], 'extra_info.flight_route'
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试使用 description（通常包含正确的IATA代码）
    if ref.description and len(ref.description) >= 7:  # 至少包含 XXX-XXX
        return ref.description, 'description'

    # 最后使用 detailed_description
    return ref.detailed_description, 'detailed_description'


def find_flight_refs_missing_segments():
    """
    查找没有 ProjectFlightSegment 记录的机票REF
    """
    print("[DEBUG] 查找缺少航段记录的机票REF...")

    # 获取机票业务类型ID
    flight_type = BusinessType.query.filter(
        db.or_(
            BusinessType.code == 'flight',
            BusinessType.code == 'air_ticket',
            BusinessType.name == '机票',
            BusinessType.name.like('%机票%')
        )
    ).first()

    if not flight_type:
        print("错误：未找到机票业务类型")
        return []

    print(f"使用机票类型: ID={flight_type.id}, code='{flight_type.code}', name='{flight_type.name}'")

    # 查找所有机票类型的REF
    flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_type.id).all()
    print(f"找到 {len(flight_refs)} 个机票类型的REF")

    refs_missing_segments = []
    for ref in flight_refs:
        # 检查是否有 ProjectFlightSegment 记录
        segment_count = ProjectFlightSegment.query.filter_by(ref_id=ref.id).count()
        if segment_count == 0:
            refs_missing_segments.append(ref)

    print(f"其中 {len(refs_missing_segments)} 个REF缺少航段记录")
    return refs_missing_segments


def create_segments_from_ref(ref, dry_run=True):
    """
    从REF创建 ProjectFlightSegment 和 ProjectFlightPassenger 记录
    """
    result = {
        'ref_number': ref.ref_number,
        'status': 'skipped',
        'message': '',
        'segments_created': 0,
        'passengers_created': 0
    }

    # 获取 ProjectHeader
    project_header = db.session.get(ProjectHeader, ref.header_id)
    hid = project_header.hid if project_header else None

    # 获取乘客名 - 优先从 extra_info 获取
    leader_name = None
    if ref.extra_info:
        try:
            extra = json.loads(ref.extra_info)
            leader_name = extra.get('leader_name') or extra.get('pax_names_display')
        except:
            pass
    if not leader_name and project_header:
        leader_name = project_header.leader_name
    if not leader_name:
        leader_name = 'Guest'

    # 获取航线描述（优先使用包含正确IATA代码的字段）
    route_desc, source = get_route_description(ref)

    # 解析航段
    segments = parse_route_segments(route_desc)

    # 计算基础日期（使用REF创建日期 + 10天作为航班日期）
    base_date = (ref.created_at or datetime.now()).date() + timedelta(days=10)

    print(f"\nREF {ref.ref_number}:")
    print(f"  HID: {hid}")
    print(f"  数据来源: {source}")
    print(f"  航线描述: {route_desc}")
    print(f"  解析航段: {segments if segments else '无法解析'}")
    print(f"  乘客: {leader_name}")
    print(f"  售价: {ref.selling_price}, 成本: {ref.cost_price}")

    if not segments:
        result['message'] = '无法从描述中解析航段'
        print(f"  跳过：无法解析航段")
        return result

    if dry_run:
        result['status'] = 'dry_run'
        result['segments_created'] = len(segments)
        result['passengers_created'] = 1
        result['message'] = f'将创建 {len(segments)} 个航段, 1 个乘客'
        return result

    try:
        # 创建航段
        for idx, (dep_airport, arr_airport) in enumerate(segments):
            is_morning = (idx % 2 == 0)
            dep_time, arr_time = generate_flight_time(base_date, idx, is_morning)
            flight_number = f"JE{idx + 1:02d}"

            segment = ProjectFlightSegment(
                ref_id=ref.id,
                flight_number=flight_number,
                departure_airport=dep_airport,
                arrival_airport=arr_airport,
                departure_time=dep_time,
                arrival_time=arr_time,
                cabin_class='Economy',
                cabin_code='Y',
                status='confirmed'
            )
            db.session.add(segment)
            result['segments_created'] += 1
            print(f"  创建航段: {flight_number} {dep_airport}->{arr_airport}")

        # 检查是否已有乘客
        existing_passengers = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).count()
        if existing_passengers == 0 and leader_name:
            passenger = ProjectFlightPassenger(
                ref_id=ref.id,
                name=leader_name,
                passenger_type='adult',
                selling_price=ref.selling_price,
                cost_price=ref.cost_price
            )
            db.session.add(passenger)
            result['passengers_created'] = 1
            print(f"  创建乘客: {leader_name}")

        db.session.commit()
        result['status'] = 'success'
        result['message'] = f'成功创建 {result["segments_created"]} 个航段'

    except Exception as e:
        db.session.rollback()
        result['status'] = 'error'
        result['message'] = str(e)
        print(f"  错误: {e}")

    return result


def main(execute=False):
    """
    主函数
    """
    with app.app_context():
        print("=" * 60)
        print("机票REF航段数据修复脚本")
        print("=" * 60)
        print(f"模式: {'执行' if execute else '预览'}")
        print()

        # 查找缺少航段的REF
        refs_missing = find_flight_refs_missing_segments()

        if not refs_missing:
            print("\n没有需要修复的REF")
            return

        print(f"\n找到 {len(refs_missing)} 个需要修复的REF")

        # 处理结果统计
        stats = {
            'total': len(refs_missing),
            'success': 0,
            'error': 0,
            'skipped': 0,
            'total_segments': 0,
            'total_passengers': 0
        }

        for ref in refs_missing:
            result = create_segments_from_ref(ref, dry_run=not execute)

            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'error':
                stats['error'] += 1
            elif result['status'] == 'skipped':
                stats['skipped'] += 1
            elif result['status'] == 'dry_run':
                stats['success'] += 1  # 预览模式下计为成功

            stats['total_segments'] += result['segments_created']
            stats['total_passengers'] += result['passengers_created']

        # 输出统计
        print("\n" + "=" * 60)
        print("统计结果")
        print("=" * 60)
        print(f"总计REF数: {stats['total']}")
        print(f"处理成功: {stats['success']}")
        print(f"处理失败: {stats['error']}")
        print(f"跳过: {stats['skipped']}")
        print(f"创建航段: {stats['total_segments']}")
        print(f"创建乘客: {stats['total_passengers']}")

        if not execute:
            print("\n" + "-" * 60)
            print("这是预览模式，未实际修改数据库")
            print("要执行修复，请运行: python scripts/20260126_fix_flight_orders_missing_data.py --execute")


if __name__ == '__main__':
    execute_mode = '--execute' in sys.argv
    main(execute=execute_mode)
