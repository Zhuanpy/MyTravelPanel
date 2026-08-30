import time
import pymysql
try:
    import pyautogui  # 在无图形环境（Linux服务器）可能不可用
except Exception:
    pyautogui = None
import datetime
import os


def get_times():
    """
    get time
    """
    str_time = time.strftime('%Y{}%m{}%d{} %X')
    str_time = str_time.format('年', '月', '日')
    return str_time


# 假设有10个航班信息

class FlightData:

    @classmethod
    def generate_booking_code_text(cls, num: int, data: dict, flight_date: str):
        """
        根据提供的航班信息生成预定代码。
        :param num: 航班的序号，通常用于标识航班的顺序
        :param data: 包含航班时刻表、航空公司代码等信息的字典，具体结构如下：
                     - 'airline_code': 航空公司代码，例如 'MU'
                     - 'airline_num': 航班号，例如 '568'
                     - 'schedule_city': 包含出发城市和到达城市的字符串，用空格分隔
                     - 'schedule_timing': 包含出发时间和到达时间的字符串，用空格分隔
        :param flight_date: 航班日期，表示航班的具体飞行日期
        :return: 返回格式化的预定代码字符串，或者错误信息
        """

        try:
            # 确保航班日期去除空格并转换为大写
            flight_date = flight_date.replace(" ", "").upper()
            # 航班时刻表数据
            city = data['schedule_city'].split(" ")
            city = [item for item in city if item != ""]

            timings = data['schedule_timing'].split(" ")
            timings = [item for item in timings if item != ""]

            departure_city = city[0]
            arrive_city = city[1]
            departure_timing = timings[0]
            arrive_timing = timings[1]

            flight_num = data['airline_num'].rjust(4)  # 补 齐4位数
            arrive_timing = arrive_timing.rjust(5) # 补 齐5位数

            result = (f" {num}. {data['airline_code']} {flight_num} Y  "
                      f"{flight_date} {departure_city}{arrive_city} HK1  "
                      f"{departure_timing}  {arrive_timing}  O        E FR")

            return result

        except pymysql.MySQLError as e:
            # 捕获并返回数据库错误
            return f"Database error: {e}"

        except Exception as e:
            # 捕获并返回其他错误
            return f"An error occurred: {e}"


def take_screenshot(save_path="screenshots"):
    # 创建保存路径文件夹（如果不存在）
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 获取当前时间作为文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_filename = os.path.join(save_path, f"screenshot_{timestamp}.png")

    # 截图并保存（无GUI环境时跳过）
    if pyautogui is None:
        print("pyautogui 不可用：服务器可能无图形环境，已跳过截图。")
        return None
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_filename)

    print(f"截图已保存为 {screenshot_filename}")


if __name__ == "__main__":
    # 指定保存路径
    time.sleep(3)
    save_directory = "E:\WORKING\A-AIR_TICKET/MyScreenshots"  # 修改为你想要的保存路径
    print(f"正在进行截图，图片将保存到：{save_directory}")
    take_screenshot(save_directory)
