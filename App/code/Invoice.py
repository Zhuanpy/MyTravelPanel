import pandas as pd
import os

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)


class CountHid:

    def __init__(self, booking_path:str, name="Zz"):

        self._path = os.path.join(booking_path, name)

    def read_all_inv(self, complete_month=0):

        """
        读取所有发票文件并处理数据。

        参数:
        complete_month (int): 完整月份的截止时间，格式为 'yyyymm'，用于过滤早于该月份的文件。

        返回:
        pd.DataFrame: 合并后的发票数据。
        """

        # 定义发票文件夹路径
        path = os.path.join(self._path, 'Invoice')
        files = os.listdir(path) # 获取所有文件列表
        datas = pd.DataFrame()  # 初始化空数据框

        for f in files:

            y = f[:6]  # 文件名前6位为年月，格式 'yyyymm'
            if int(y) < int(complete_month):
                continue

            name = os.path.join(path, f)

            df = pd.read_excel(name, sheet_name='Sheet1', header=None)  # , names=columns)

            # 删除不需要的列
            df = df.drop(columns=[1, 7, 9, 10, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28])

            # 删除关键列的空值行
            df = df.dropna(subset=[0, 2])

            # 强制转换列的类型，0和2列为整数，3和5列为字符串
            df[[0, 2]] = df[[0, 2]].astype(int)
            df[[3, 5]] = df[[3, 5]].astype(str)

            # 日期调整，将3和5列中的日期格式转换为标准日期格式
            df[3] = df[3].str[2:]
            df[5] = df[5].str[2:]
            df[3] = pd.to_datetime(df[3], format='%d-%m-%y')
            df[5] = pd.to_datetime(df[5], format='%d-%m-%y')

            # 合并数据
            datas = pd.concat([datas, df], ignore_index=True)

        return datas

    def read_all_hid(self, complete_month=0):
        hid_path = os.path.join(self._path, 'HID')
        hid_files = os.listdir(hid_path)

        datas = pd.DataFrame()

        for f in hid_files:
            y = f[:6]

            if int(y) < int(complete_month):
                continue

            name = os.path.join(hid_path, f)
            df = pd.read_excel(name, sheet_name='Sheet1', header=None)

            # 使用列名而不是列索引，提高代码可读性
            # 注意：如果不确定列名，可以考虑输出 df.columns 看看具体的列名
            df = df.drop(columns=[1, 11, 6, 12, 13, 14, 15])

            # 使用 drop na 处理缺失值，确保删除的是非空值而不是任何值
            df = df.dropna(subset=[0, 2])
            df[0] = df[0].astype(int)
            df[[2, 4]] = df[[2, 4]].astype(str)

            # 调整日期
            df[2] = df[2].str[2:]
            df[4] = df[4].str[2:]
            df[2] = pd.to_datetime(df[2], format='%d-%m-%y')
            df[4] = pd.to_datetime(df[4], format='%d-%m-%y')

            datas = pd.concat([datas, df], ignore_index=True)

        return datas

    def read_disputed(self):
        """
        读取争议账单文件，并将其转换为数组。

        返回:
        numpy.ndarray: 包含争议账单信息的数组。
        """

        # 拼接争议账单文件路径
        disputed_file_path = os.path.join(self._path, 'disputed.txt')

        # 使用 with 语句确保文件正确关闭
        with open(disputed_file_path, 'r') as file:
            data = pd.read_csv(file, header=None )

        # 将数据转换为numpy数组并返回
        li = data.values
        return li

    def find_no_inv_booking(self, pre_month='2024-08'):
        """
        查找未开具发票的预订信息，并计算利润总额。

        参数:
        pre_month (str): 指定的月份，用于过滤前几个月的订单，格式为 'YYYY-MM'。

        返回:
        tuple: 包含总利润和前几个月利润的元组 (profits, pre_sum)。
        """

        # 获取记录账单完成进度的文件路径
        complete_path = os.path.join(self._path, 'complete.txt')

        # 读取账单完成的月份信息
        with open(complete_path, 'r') as cm_file:
            complete_month = int(cm_file.readline().strip())

        # 读取所有发票和预订信息
        inv = self.read_all_inv(complete_month)
        hid = self.read_all_hid(complete_month)

        # 清除不正常订单：去除发票中已存在的订单，且过滤掉盈利为0的订单
        hid = hid[~hid[0].isin(list(inv[0]))]
        hid = hid[hid[7] != 0]

        # 清除已经发现有争议订单
        disputed = self.read_disputed()
        hid = hid[~hid[0].isin(disputed)]

        hid = hid.sort_values(by=[0])
        hid = hid.reset_index(drop=True)
        profits = hid[9].sum()

        # 获取最新做账进度，做账至几月份，并保存记录
        last_month = hid[2][0].strftime('%Y%m')
        with open(complete_path, 'w') as f:
            f.write('\n'.join([last_month]))

        # 整理前几个月的订单并计算利润
        pre_booking = hid[hid[2] < pd.to_datetime(pre_month)]
        pre_sum = pre_booking[9].sum()  # 计算前几个月订单的利润

        # r = f'全部未结算总额：SGD {int(profits)}; \n截至{pre_month[:4]}年{pre_month[-2:]}月的未结算总额: SGD {int(pre_sum)}'

        return int(profits), int(pre_sum)


class CountMonth:

    def __init__(self, start_month=202304, end_month=202307, file_path: str = None, name="Zz", ):

        """
        初始化函数，设置起始月份、结束月份以及文件路径。
        如果未提供 file_path，则使用默认路径 'E:/WORKING/B-账单/BOOKING/{name}'。

        参数:
        start_month (int): 起始月份，格式为 YYYYMM。
        end_month (int): 结束月份，格式为 YYYYMM。
        file_path (str): 文件路径，默认为 None。
        name (str): 名称，用于构建默认路径时使用。

        """

        self._path = file_path if file_path else f'E:/WORKING/B-账单/BOOKING/{name}'
        self.start_month = start_month
        self.end_month = end_month

    def import_my_performance(self, ):

        """
        导入绩效数据，遍历文件夹中的 Excel 文件，过滤出符合月份范围的数据。
        数据清理后，按日期和编号排序，并计算首尾 HID。

        返回:
        performance (DataFrame): 包含清理后绩效数据的 Pandas DataFrame。
        """

        # 设置 HID 文件夹路径
        hid_path = os.path.join(self._path, 'HID')
        hid_files = os.listdir(hid_path)
        performance = pd.DataFrame()

        for f in hid_files:

            # 获取文件名前 6 位作为年份和月份
            y = f[:6]

            # 检查月份是否在范围内
            if int(y) < int(self.start_month) or int(y) > self.end_month:
                continue

            # 读取 Excel 文件
            name = os.path.join(hid_path, f)
            df = pd.read_excel(name, sheet_name='Sheet1', header=None)

            # 删除不需要的列
            df = df.drop(columns=[1, 11, 6, 13, 14, 15])
            df = df.dropna(subset=[12])
            df[0] = df[0].astype(int)
            df[[2, 4]] = df[[2, 4]].astype(str)

            # 调整日期格式
            df[2] = df[2].str[2:]  # 去除日期中的前两位字符
            df[4] = df[4].str[2:]

            df[2] = pd.to_datetime(df[2], format='%d-%m-%y')
            df[4] = pd.to_datetime(df[4], format='%d-%m-%y')

            # 按日期和编号排序
            df = df.sort_values(by=[2, 0]).reset_index(drop=True)

            # 获取首尾 HID
            hids = df[0].values
            first_hid = hids[0]
            last_hid = hids[-1]

            df['firstHid'] = first_hid
            df['lastHid'] = last_hid

            # 将当前文件的数据合并到总的 performance DataFrame 中
            performance = pd.concat([performance, df], ignore_index=True)

        # 按编号排序并格式化月份
        performance[2] = pd.to_datetime(performance[2])
        performance = performance.sort_values(by=0)
        performance['month'] = performance[2].dt.strftime('%Y-%m')

        return performance


if __name__ == '__main__':
    # name = "Ly"
    # name = name
    count = CountHid()
    count.find_no_inv_booking()

