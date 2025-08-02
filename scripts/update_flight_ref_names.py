#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机票REF名称标准化脚本
根据当前的命名规则，更新所有现有的机票REF名称
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.projects.BookingProject import ProjectRef, ProjectFlightSegment
from App import db

def generate_flight_ref_name(departure_airports, arrival_airports, departure_dates):
    """根据航段信息生成REF名称：支持多航段"""
    if not departure_airports or not arrival_airports or not departure_dates:
        return '机票订单'
    
    # 收集所有有效的航段信息
    valid_segments = []
    first_dep_date = None
    
    for i, (dep_airport, arr_airport, dep_date) in enumerate(zip(departure_airports, arrival_airports, departure_dates)):
        if dep_airport and arr_airport and dep_date:
            if first_dep_date is None:
                first_dep_date = dep_date
            valid_segments.append((dep_airport, arr_airport))
    
    if not valid_segments or not first_dep_date:
        return '机票订单'
    
    # 格式化日期为 DDMON 格式 (例如: 12AUG)
    try:
        date_obj = datetime.strptime(first_dep_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d%b').upper()
    except ValueError:
        formatted_date = first_dep_date
    
    # 根据航段数量和类型生成不同的名称格式
    if len(valid_segments) == 1:
        # 单航段：出发日期 + 出发机场-到达机场
        dep_airport, arr_airport = valid_segments[0]
        ref_name = f"{formatted_date} {dep_airport}-{arr_airport}"
    
    elif len(valid_segments) == 2:
        # 双航段：检查是否为往返
        dep1, arr1 = valid_segments[0]
        dep2, arr2 = valid_segments[1]
        
        if dep1 == arr2 and arr1 == dep2:
            # 往返：出发日期 + 出发机场-到达机场-出发机场
            ref_name = f"{formatted_date} {dep1}-{arr1}-{dep1}"
        else:
            # 非往返：出发日期 + 出发机场-到达机场-最终到达机场
            ref_name = f"{formatted_date} {dep1}-{arr1}-{arr2}"
    
    else:
        # 多航段：构建完整的航线路径
        route_parts = []
        for i, (dep_airport, arr_airport) in enumerate(valid_segments):
            if i == 0:
                # 第一个航段：包含出发机场
                route_parts.append(f"{dep_airport}-{arr_airport}")
            else:
                # 后续航段：只包含到达机场
                route_parts.append(arr_airport)
        
        # 检查是否为往返
        first_dep, first_arr = valid_segments[0]
        last_dep, last_arr = valid_segments[-1]
        
        if first_dep == last_arr and first_arr == last_dep:
            # 往返：出发日期 + 完整路径
            ref_name = f"{formatted_date} {'-'.join(route_parts)}"
        else:
            # 非往返：出发日期 + 完整路径
            ref_name = f"{formatted_date} {'-'.join(route_parts)}"
    
    return ref_name

def update_flight_ref_names():
    """更新所有机票REF的名称"""
    app = create_app()
    
    with app.app_context():
        # 获取机票业务类型
        from App.models.Product.BusinessType import BusinessType
        flight_business_type = BusinessType.query.filter_by(name='机票').first()
        
        if not flight_business_type:
            print("错误：未找到机票业务类型")
            return
        
        # 获取所有机票类型的REF
        flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_business_type.id).all()
        
        print(f"找到 {len(flight_refs)} 个机票REF需要更新")
        
        updated_count = 0
        skipped_count = 0
        
        for ref in flight_refs:
            try:
                # 获取该REF的所有航段
                segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()
                
                if not segments:
                    print(f"REF {ref.ref_number}: 没有找到航段信息，跳过")
                    skipped_count += 1
                    continue
                
                # 收集航段信息
                departure_airports = []
                arrival_airports = []
                departure_dates = []
                
                for segment in segments:
                    departure_airports.append(segment.departure_airport)
                    arrival_airports.append(segment.arrival_airport)
                    departure_dates.append(segment.departure_time.strftime('%Y-%m-%d'))
                
                # 生成新的名称
                new_name = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
                
                # 检查名称是否已经正确
                if ref.name == new_name:
                    print(f"REF {ref.ref_number}: 名称已经是标准格式 '{new_name}'，跳过")
                    skipped_count += 1
                    continue
                
                # 更新名称
                old_name = ref.name
                ref.name = new_name
                ref.description = new_name
                
                print(f"REF {ref.ref_number}: '{old_name}' -> '{new_name}'")
                updated_count += 1
                
            except Exception as e:
                print(f"REF {ref.ref_number}: 更新失败 - {str(e)}")
                skipped_count += 1
                continue
        
        # 提交所有更改
        try:
            db.session.commit()
            print(f"\n更新完成！")
            print(f"成功更新: {updated_count} 个REF")
            print(f"跳过: {skipped_count} 个REF")
        except Exception as e:
            db.session.rollback()
            print(f"提交失败: {str(e)}")

def preview_changes():
    """预览将要进行的更改"""
    app = create_app()
    
    with app.app_context():
        # 获取机票业务类型
        from App.models.Product.BusinessType import BusinessType
        flight_business_type = BusinessType.query.filter_by(name='机票').first()
        
        if not flight_business_type:
            print("错误：未找到机票业务类型")
            return
        
        # 获取所有机票类型的REF
        flight_refs = ProjectRef.query.filter_by(ref_type_id=flight_business_type.id).all()
        
        print(f"找到 {len(flight_refs)} 个机票REF")
        print("\n预览更改:")
        print("-" * 80)
        
        for ref in flight_refs:
            try:
                # 获取该REF的所有航段
                segments = ProjectFlightSegment.query.filter_by(ref_id=ref.id).order_by(ProjectFlightSegment.departure_time).all()
                
                if not segments:
                    print(f"REF {ref.ref_number}: 没有航段信息")
                    continue
                
                # 收集航段信息
                departure_airports = []
                arrival_airports = []
                departure_dates = []
                
                for segment in segments:
                    departure_airports.append(segment.departure_airport)
                    arrival_airports.append(segment.arrival_airport)
                    departure_dates.append(segment.departure_time.strftime('%Y-%m-%d'))
                
                # 生成新的名称
                new_name = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
                
                if ref.name != new_name:
                    print(f"REF {ref.ref_number}:")
                    print(f"  当前: '{ref.name}'")
                    print(f"  新名称: '{new_name}'")
                    print(f"  航段: {departure_airports} -> {arrival_airports}")
                    print()
                
            except Exception as e:
                print(f"REF {ref.ref_number}: 处理失败 - {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='机票REF名称标准化脚本')
    parser.add_argument('--preview', action='store_true', help='仅预览更改，不实际更新')
    parser.add_argument('--confirm', action='store_true', help='确认执行更新操作')
    
    args = parser.parse_args()
    
    if args.preview:
        print("预览模式 - 不会进行实际更改")
        preview_changes()
    elif args.confirm:
        print("确认执行更新操作...")
        update_flight_ref_names()
    else:
        print("请使用 --preview 预览更改，或使用 --confirm 确认执行更新")
        print("示例:")
        print("  python update_flight_ref_names.py --preview")
        print("  python update_flight_ref_names.py --confirm") 