# -*- coding: utf-8 -*-
"""
修复机票REF缺少航段和乘客数据的问题
从description字段解析航段信息（如 SIN/PER/SIN）
从extra_info解析乘客姓名、出发日期等
使用REF的selling_price和cost_price作为乘客票价
"""

import sys
import os
import re
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from decimal import Decimal
from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.flight.models.flight import ProjectFlightSegment, ProjectFlightPassenger
from App_new.shared.models.business_types import BusinessType


def parse_itinerary(itin_desc):
    """解析航段描述，返回机场代码列表

    支持格式：
    - SIN/PER/SIN -> ['SIN', 'PER', 'SIN']
    - SIN/TAO-NKG/SIN -> ['SIN', 'TAO', 'NKG', 'SIN'] (连字符表示中转)
    """
    if not itin_desc:
        return []

    # 先按 / 分割
    segments = itin_desc.split('/')
    airports = []

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # 处理连字符（中转）
        if '-' in seg:
            parts = seg.split('-')
            for part in parts:
                part = part.strip().upper()
                if part and len(part) >= 2:
                    airports.append(part[:3])  # 取前3位作为机场代码
        else:
            seg = seg.upper()
            if len(seg) >= 2:
                airports.append(seg[:3])

    return airports


def parse_extra_info(extra_info_str):
    """解析extra_info JSON字符串"""
    if not extra_info_str:
        return {}
    try:
        return json.loads(extra_info_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    # 尝试多种格式
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d',
        '%d/%m/%Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def parse_passenger_name(client_name):
    """解析乘客姓名，返回(姓名, 类型)

    类型：adult/child/infant
    """
    if not client_name:
        return None, 'adult'

    client_name = client_name.strip()
    passenger_type = 'adult'

    # 判断乘客类型
    upper_name = client_name.upper()
    if 'MASTER' in upper_name or 'MSTR' in upper_name:
        passenger_type = 'child'
    elif 'INFANT' in upper_name or 'INF ' in upper_name:
        passenger_type = 'infant'

    # 去掉称谓获取纯姓名
    title_pattern = r'\b(MR|MS|MISS|MASTER|MRS|MSTR|DR|PROF|INF|INFANT)\b'
    name_clean = re.sub(title_pattern, '', client_name, flags=re.IGNORECASE).strip()
    name_clean = re.sub(r'\s+', ' ', name_clean).strip()

    return name_clean or client_name, passenger_type


def fix_flight_data():
    """修复缺少航段和乘客数据的机票REF"""
    app = create_app()

    with app.app_context():
        # 获取机票类型的ID
        air_ticket_types = BusinessType.query.filter(
            db.or_(
                BusinessType.code == 'air_ticket',
                BusinessType.name_en.ilike('%Air%'),
                BusinessType.name == '机票'
            )
        ).all()

        type_ids = [t.id for t in air_ticket_types]
        print(f"机票类型ID: {type_ids}")

        if not type_ids:
            print("未找到机票业务类型")
            return

        # 查找所有机票REF
        refs = db.session.query(ProjectRef).filter(
            ProjectRef.ref_type_id.in_(type_ids)
        ).all()

        stats = {
            'total': 0,
            'segments_created': 0,
            'segments_skipped': 0,
            'passengers_created': 0,
            'passengers_skipped': 0,
            'passengers_updated': 0,
            'errors': []
        }

        for ref in refs:
            stats['total'] += 1

            # 解析extra_info
            extra_info = parse_extra_info(ref.extra_info)

            # 获取出发日期
            dep_date = parse_date(extra_info.get('dep_date'))
            if not dep_date:
                dep_date = ref.created_at or datetime.utcnow()

            # ===== 处理航段 =====
            existing_segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).count()
            if existing_segments > 0:
                stats['segments_skipped'] += 1
            else:
                # 解析航段描述
                itin_desc = ref.description or ref.detailed_description
                airports = parse_itinerary(itin_desc)

                if len(airports) >= 2:
                    try:
                        for i in range(len(airports) - 1):
                            departure_airport = airports[i]
                            arrival_airport = airports[i + 1]

                            # 使用dep_date作为基准时间
                            segment_dep_time = dep_date.replace(hour=8, minute=0, second=0, microsecond=0)
                            segment_arr_time = dep_date.replace(hour=12, minute=0, second=0, microsecond=0)

                            if i > 0:
                                segment_dep_time = segment_dep_time + timedelta(days=i)
                                segment_arr_time = segment_arr_time + timedelta(days=i)

                            segment = ProjectFlightSegment(
                                ref_id=ref.id,
                                flight_number='TBA',
                                departure_airport=departure_airport,
                                arrival_airport=arrival_airport,
                                departure_time=segment_dep_time,
                                arrival_time=segment_arr_time,
                                cabin_class='Economy',
                                cabin_code='Y',
                                status='confirmed',
                            )
                            db.session.add(segment)
                            stats['segments_created'] += 1

                        print(f"REF {ref.ref_number}: 创建 {len(airports)-1} 个航段 ({itin_desc})")
                    except Exception as e:
                        stats['errors'].append(f"REF {ref.ref_number} 航段创建失败: {str(e)}")
                else:
                    stats['errors'].append(f"REF {ref.ref_number}: 无法解析航段 '{itin_desc}'")

            # ===== 处理乘客 =====
            existing_passenger = ProjectFlightPassenger.query.filter_by(ref_id=ref.id).first()
            client_name = extra_info.get('client_name', '')

            if existing_passenger:
                # 更新现有乘客的价格信息
                updated = False
                if ref.selling_price and (not existing_passenger.selling_price or existing_passenger.selling_price == 0):
                    existing_passenger.selling_price = ref.selling_price
                    updated = True
                if ref.cost_price and (not existing_passenger.cost_price or existing_passenger.cost_price == 0):
                    existing_passenger.cost_price = ref.cost_price
                    updated = True
                if updated:
                    stats['passengers_updated'] += 1
                else:
                    stats['passengers_skipped'] += 1
            elif client_name:
                # 创建新乘客记录
                try:
                    name_clean, passenger_type = parse_passenger_name(client_name)

                    passenger = ProjectFlightPassenger(
                        ref_id=ref.id,
                        name=name_clean,
                        passenger_type=passenger_type,
                        selling_price=ref.selling_price or Decimal('0'),
                        cost_price=ref.cost_price or Decimal('0'),
                    )
                    db.session.add(passenger)
                    stats['passengers_created'] += 1
                    print(f"REF {ref.ref_number}: 创建乘客 {name_clean} (售价:{ref.selling_price}, 成本:{ref.cost_price})")
                except Exception as e:
                    stats['errors'].append(f"REF {ref.ref_number} 乘客创建失败: {str(e)}")
            else:
                stats['passengers_skipped'] += 1

        # 提交事务
        try:
            db.session.commit()
            print(f"\n{'='*50}")
            print(f"修复完成!")
            print(f"{'='*50}")
            print(f"总REF数量: {stats['total']}")
            print(f"航段 - 创建: {stats['segments_created']}, 跳过: {stats['segments_skipped']}")
            print(f"乘客 - 创建: {stats['passengers_created']}, 更新: {stats['passengers_updated']}, 跳过: {stats['passengers_skipped']}")
            print(f"错误: {len(stats['errors'])}")

            if stats['errors']:
                print(f"\n错误详情 (前20条):")
                for err in stats['errors'][:20]:
                    print(f"  - {err}")
                if len(stats['errors']) > 20:
                    print(f"  ... 还有 {len(stats['errors']) - 20} 条错误")

        except Exception as e:
            db.session.rollback()
            print(f"提交失败: {str(e)}")


if __name__ == '__main__':
    fix_flight_data()
