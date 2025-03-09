import requests
from bs4 import BeautifulSoup
import pandas as pd
import time


class AthinaBooking:

    @classmethod
    def return_text(cls, airline: str, flight_num: str, dep_airport: str,
                    arr_airport: str, dep_time: str, arr_time: str):
        """
        示例用法结果
        1. TR  124 Y  12MAY SINCSX HS1  1805   2250
        """

        r = f"1. {airline}  {flight_num} E  30JUN {dep_airport}{arr_airport} HS1  {dep_time}  {arr_time} "
        return r


def download_airport_code():

    for i in range(1, 290):

        url = f'https://airportcode.bmcx.com/{i}__airportcode/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 找到包含机场信息的表格
        airport_table = soup.find('table')
        # 遍历表格行
        airport_df = pd.read_html(str(airport_table), header=0)
        airport_df = airport_df[1]

        # 保存为CSV文件
        airport_df.to_csv('airport_data.csv', mode='a', header=False, index=False)
        print(f"download page to {i}")
        time.sleep(1)

    return True



if __name__ == '__main__':
    # download_airport_code()
    pass
