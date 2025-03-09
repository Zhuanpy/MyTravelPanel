import requests
import pandas as pd
from datetime import datetime
import os


# 定义函数来获取航班数据
def fetch_flight_data(api_key, dep_iata, arr_iata):
    # 定义 API URL 和请求参数
    url = 'http://api.aviationstack.com/v1/flights'
    params = {
        'access_key': api_key,
        'dep_iata': dep_iata,  # 出发机场 IATA 代码
        'arr_iata': arr_iata  # 到达机场 IATA 代码
    }

    try:
        # 发起请求并检查是否成功
        response = requests.get(url, params=params)
        response.raise_for_status()  # 确保请求没有问题
        data = response.json()
        flights_data = data.get('data', [])
        return flights_data

    except requests.RequestException as e:
        # 检查错误信息是否包含 "429 Client Error: Too Many Requests for url"
        if "429 Client Error: Too Many Requests for url" in str(e):
            print("请求失败：过多请求。程序结束。")
            raise SystemExit(e)  # 结束程序
        else:
            print(f"请求失败：{e}")
            return []  # 返回 None 或处理其他错误


# 辅助函数：解析时间
def parse_time(time_str):
    time_obj = datetime.fromisoformat(time_str)
    return time_obj.strftime("%H:%M"), time_obj.date()


# 处理航班数据的函数
def process_flight_data(flights_data):
    def find_data(data1):
        departure = data1.get("departure", {})
        arrival = data1.get("arrival", {})
        airline = data1.get("airline", {})
        flight = data1.get("flight", {})

        # 提取并格式化时间
        departure_scheduled_time, departure_scheduled_date = parse_time(departure.get('scheduled'))
        arrival_scheduled_time, arrival_scheduled_date = parse_time(arrival.get('scheduled'))

        # 如果到达日期比出发日期晚，加上特殊标记
        if arrival_scheduled_date > departure_scheduled_date:
            arrival_scheduled_time = f"#{arrival_scheduled_time}"

        # 组合航班和航空公司信息
        airline_name = airline.get("name")
        airline_iata = airline.get("iata")
        flight_number = flight.get("number", "")
        full_flight_number = f"{airline_iata}{flight_number}"
        route_iata = f"{departure.get('iata')} {arrival.get('iata')}"

        return [
            departure_scheduled_time,
            arrival_scheduled_time,
            airline_name,
            airline_iata,
            flight_number,
            full_flight_number,
            route_iata
        ]

    # 创建包含所有数据的列表
    data_list = [find_data(flight) for flight in flights_data]

    # 转换为 Pandas DataFrame
    df = pd.DataFrame(data_list, columns=[
        "Departure Time", "Arrival Time", "Airline Name", "Airline IATA",
        "Flight Number", "Full Flight Number", "Route IATA"
    ])

    return df


# 主函数：获取并处理数据
def get_flight_data(api_key, dep_iata, arr_iata):
    # 获取航班数据
    flights_data = fetch_flight_data(api_key, dep_iata, arr_iata)

    # 处理航班数据
    if flights_data:
        df = process_flight_data(flights_data)
        return df
    else:
        return None


# 存储数据的函数，每次追加写入
def save_flight_data(flight_df, output_file):
    file_exists = os.path.isfile(output_file)
    flight_df.to_csv(output_file, index=False, mode='a', header=not file_exists)


# 下载和存储航班数据
def download_and_store_flights(api_key, airport_data, output_file):
    for index in airport_data.index:
        dep_iata = airport_data.loc[index, "Departure Airport"]
        arr_iata = airport_data.loc[index, "Arrival Airport"]

        print(f"获取航班数据：{dep_iata} -> {arr_iata}")
        flight_df = get_flight_data(api_key, dep_iata, arr_iata)

        if flight_df is not None and not flight_df.empty:
            save_flight_data(flight_df, output_file)
            print(f"成功存储 {dep_iata} -> {arr_iata} 的航班数据")

        else:
            print(f"未能获取航班数据：{dep_iata} -> {arr_iata}")


# 主函数，管理数据下载和存储
def main(api_key, input_file, output_file):
    """
    主函数，处理数据下载和存储。

    参数：
    api_key (str): API 密钥，用于数据下载。
    input_file (str): 包含待处理航班数据的输入 CSV 文件路径。
    output_file (str): 包含已下载数据的 CSV 文件路径。
    """

    download_data = pd.read_csv(output_file)
    download_data = download_data.drop_duplicates(subset=["Route IATA"]).reset_index(drop=True)
    download_data['Route IATA'] = download_data['Route IATA'].str.replace(' ', '/')
    download_data = download_data.drop_duplicates(subset=["Route IATA"])

    # 排除已经下载的数据
    airport_data = pd.read_csv(input_file)
    filtered_data = airport_data[~airport_data["Combined"].isin(download_data['Route IATA'])]

    # 选择必要的列并重置索引
    filtered_data = filtered_data[["route", "Departure Airport", "Arrival Airport", "Combined"]].reset_index(drop=True)
    filtered_data = filtered_data.drop_duplicates(subset="Combined")
    print(filtered_data)
    # exit()
    # 调用数据下载和存储函数
    download_and_store_flights(api_key, filtered_data, output_file)


# 调用主函数
if __name__ == "__main__":
    API_KEY = '11616410fa3787c227f606509ad76108'
    INPUT_FILE = 'route_data.csv'  # 需要下载的机场数据
    OUTPUT_FILE = 'flight_timing.csv'  # 存储航班信息的文件
    main(API_KEY, INPUT_FILE, OUTPUT_FILE)
