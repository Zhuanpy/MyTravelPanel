from datetime import datetime

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

# 测试用例
print("=== 测试机票REF名称生成 ===")

# 测试1：单航段
print("\n1. 单航段测试:")
departure_airports = ['SIN']
arrival_airports = ['TAO']
departure_dates = ['2024-08-12']
result = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
print(f"输入: SIN -> TAO")
print(f"输出: {result}")

# 测试2：往返双航段
print("\n2. 往返双航段测试:")
departure_airports = ['SIN', 'TAO']
arrival_airports = ['TAO', 'SIN']
departure_dates = ['2024-08-12', '2024-08-13']
result = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
print(f"输入: SIN -> TAO, TAO -> SIN")
print(f"输出: {result}")

# 测试3：非往返双航段
print("\n3. 非往返双航段测试:")
departure_airports = ['SIN', 'TAO']
arrival_airports = ['TAO', 'NKG']
departure_dates = ['2024-08-12', '2024-08-13']
result = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
print(f"输入: SIN -> TAO, TAO -> NKG")
print(f"输出: {result}")

# 测试4：多航段
print("\n4. 多航段测试:")
departure_airports = ['SIN', 'TAO', 'NKG']
arrival_airports = ['TAO', 'NKG', 'SIN']
departure_dates = ['2024-08-12', '2024-08-13', '2024-08-14']
result = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
print(f"输入: SIN -> TAO, TAO -> NKG, NKG -> SIN")
print(f"输出: {result}")

# 测试5：多航段非往返
print("\n5. 多航段非往返测试:")
departure_airports = ['SIN', 'TAO', 'NKG']
arrival_airports = ['TAO', 'NKG', 'HKG']
departure_dates = ['2024-08-12', '2024-08-13', '2024-08-14']
result = generate_flight_ref_name(departure_airports, arrival_airports, departure_dates)
print(f"输入: SIN -> TAO, TAO -> NKG, NKG -> HKG")
print(f"输出: {result}") 