from datetime import datetime


def organize_text(texts):
    """
    解析并组织航班信息文本，返回结构化的航班信息列表。

    :param texts: 包含航班信息的字符串，每个航班信息用换行符分隔。
    :return: 返回处理后的航班信息列表，结构化数据方便后续处理。
    """

    """
    # text：
    #  1. MU  568 S  05AUG SINPVG HK1  1635   2205  O*       E SA  1
    #  2. MU 6561 B  06AUG PVGHRB HK1  0755   1050  O*       E SU  1
    """
    # 将输入的文本按行分割
    lines = texts.splitlines()

    def format_time(time_str):
        """
        格式化时间，确保时间为 hh:mm 格式。

        :param time_str: 时间字符串（如 1635 或 0525）
        :return: 格式化后的时间字符串（如 16:35 或 05:25）
        """
        if len(time_str) == 5:
            return f'{time_str[:3]}:{time_str[-2:]}'

        else:
            return f'{time_str[:2]}:{time_str[-2:]}'

    lis = []
    for line in lines:
        # 如果行太短，则跳过该行
        if len(line) < 10:
            continue

        # 按空格分割航班信息
        li = line.split()

        # 移除多余的空字符串
        li = [item for item in li if item]
        print("li:", li)
        # 如果信息项超过10个，进一步处理时间和机场代码

        if len(li) < 10:
            continue
        # 格式化机场代码（如 PVG - SIN）
        li[5] = f'{li[5][:3]} - {li[5][-3:]}'

        # 格式化出发时间和到达时间
        li[7] = format_time(li[7])
        li[8] = format_time(li[8])

        # 如果航班号长度小于4，填充前导零使其长度为4
        if len(li[2]) < 4:
            li[2] = li[2].rjust(4)

        # 将处理后的航班信息添加到最终列表中
        lis.append(li)

    return lis


def format_flight_info(city_language, texts: str, language='CN', luggage=None, price=None):
    """
    根据给定的航班信息，翻译成中文或英文，并根据不同语言生成格式化的航班信息。
    :param city_language: 一个函数，用于根据机场代码返回对应城市名称的中文或英文名称。
    :param texts: 包含航班信息的字符串，以换行符分隔每一段航班信息。
    :param language: 'CN' 表示中文，'EN' 表示英文，默认为中文。
    :param luggage: 行李信息，用于输出时添加至最终行程信息中。
    :param price: 票价信息，用于输出时添加至最终行程信息中。
    :return: 格式化的航班信息字符串。
    """

    def convert_date_format(original_date: str):
        """ 将月份名称转换为中文格式 """
        month_mapping = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
                         'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}
        try:
            parsed_date = datetime.strptime(original_date, '%d%b')
            month_number = month_mapping[parsed_date.strftime('%b').upper()]
            new_date_str = f'{month_number}月{parsed_date.strftime("%d")}号'
            return new_date_str

        except ValueError:

            return "无效的日期格式"

    def format_template(num, dep_code, arr_code, air_code, flight_code, departure_date, time_departure, time_arrival, language):
        """
        根据语言格式化航班模板。
        """
        if language == 'CN':
            return f""" {num}{dep_code} - {arr_code}, 航班号：{air_code}{flight_code}，\n {departure_date}，出发：{time_departure} - 抵达：{time_arrival} \n\n"""

        else:
            return f""" {num}{dep_code} - {arr_code}, Flight No: {air_code}{flight_code},\n {departure_date}, Departure: {time_departure} - Arrival: {time_arrival}\n\n """

    # 组织和提取航班信息
    lis = organize_text(texts)

    # 初始化最终生成的行程信息列表
    itinerary_list = []

    # 遍历处理每个航班信息
    for li in lis:

        iti_num = li[0]
        airline_code = li[1]
        flight_code = li[2]
        departure_date = li[4]
        airport_code= li[5]
        departure_time= li[7]
        arrival_time = li[8]

        # 提取出发和到达机场代码
        dep_iata = airport_code[:3]
        arr_iata = airport_code[-3:]

        dep_city_language = city_language(dep_iata)
        arr_iata_language = city_language(arr_iata)

        # 如果是中文，则需要将日期格式进行转换
        if language == 'CN':
            departure_date = convert_date_format(departure_date)

        # 格式化航班信息
        dep_code = dep_city_language[0] if language == 'CN' else dep_city_language[1]
        arr_code = arr_iata_language[0] if language == 'CN' else arr_iata_language[1]

        itinerary_list.append(format_template(iti_num, dep_code, arr_code,
                                              airline_code, flight_code,
                                              departure_date, departure_time,
                                              arrival_time, language))

    # 拼接所有的航班信息
    itn = ''.join(itinerary_list)

    # 添加票价和行李信息
    if price:
        itn += f"{'票价' if language == 'CN' else 'Fare'}: {price}; "

    if luggage:
        itn += f"\n{'行李' if language == 'CN' else 'Luggage'}: {luggage};"

    return itn


if __name__ == "__main__":
    # # 使用示例
    T = """
     1. SC 8062 T  24JAN SINTNA UC1  0055   0710             FR
     2. SC 8042 Y  24JAN TNADLC UC1  1440   1540             FR
    """
    data = organize_text(T)
    print(data)
