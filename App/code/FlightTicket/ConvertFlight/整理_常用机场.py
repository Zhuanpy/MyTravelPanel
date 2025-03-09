import pandas as pd
import os


def read_all_airport():
    # 设置显示所有列
    pd.set_option('display.max_columns', None)

    # 定义目录路径
    directory = r"E:\WORKING\B-账单\BOOKING\Zz\Invoice"

    # 获取目录下所有 Excel 文件（.xls 和 .xlsx）
    excel_files = [f for f in os.listdir(directory) if f.endswith('.xls') or f.endswith('.xlsx')]

    # 初始化一个空列表来存储每个文件的 DataFrame
    all_dataframes = []

    # 遍历所有文件并读取
    for file in excel_files:
        file_path = os.path.join(directory, file)

        # 读取 Excel 文件的第一个 sheet（可以根据需要调整）
        df = pd.read_excel(file_path, header=None)
        # 将数据添加到列表中
        all_dataframes.append(df)

    # 合并所有数据（可以根据需要选择 concat、merge 等操作）
    data = pd.concat(all_dataframes, ignore_index=True)

    data = data[[6]]

    # 保留包含 '/' 的行
    data = data[data[6].str.contains("/", na=False)]
    data = data[~data[6].str.contains("-")].reset_index(drop=True)

    # 计算每个航线的出现次数
    counts = data[6].value_counts()

    # 将结果转换为 DataFrame
    counts_df = counts.reset_index()

    counts_df.columns = ["route", "count"]
    counts_df = counts_df[["route"]]

    counts_df.to_csv("常用机场代码.csv", header=False, index=False)

    return counts_df


def process_airport_codes(csv_file, output_file):
    """
        处理 CSV 文件中的机场航线数据，提取航段对，并将结果保存到新的 CSV 文件中。

        参数：
        csv_file (str): 输入的 CSV 文件路径，包含航线数据。文件应只有一列，航线字符串以 '/' 分隔。
        output_file (str): 输出的 CSV 文件路径，将保存处理后的航段数据。

        功能：
        - 从 CSV 文件中读取航线数据。
        - 提取航段对，生成所有可能的出发机场和抵达机场对。
        - 将航段对展开成独立的行，并去重。
        - 将处理后的数据保存到指定的 CSV 文件中。
    """

    # 将 CSV 文件读取为 DataFrame
    df = pd.read_csv(csv_file, header=None, names=['route'])
    print(df)

    # 定义函数来提取所有航段对
    def extract_segments(route):
        # 使用 "/" 分割航线字符串
        airports = route.split('/')

        # 生成所有航段对
        segments = [(airports[i], airports[i + 1]) for i in range(len(airports) - 1)]

        return segments

    # 应用函数并展开生成的所有航段对
    df['segments'] = df['route'].apply(extract_segments)

    # 将列表展开成 DataFrame
    segments_df = df.explode('segments')

    # 分别提取出发机场和抵达机场
    segments_df[['Departure Airport', 'Arrival Airport']] = pd.DataFrame(segments_df['segments'].tolist(),
                                                                         index=segments_df.index)
    # 删除原始的 segments 列
    segments_df = segments_df.drop(columns='segments')

    # 添加合并列
    segments_df['Combined'] = segments_df['Departure Airport'] + '/' + segments_df['Arrival Airport']
    segments_df = segments_df.drop_duplicates(subset=["Combined"]).reset_index(drop=True)

    # 打印整理后的表格并保存到 CSV 文件
    segments_df.to_csv(output_file, index=False)

    print(f"整理后的数据已保存到 {output_file}")


if __name__ == "__main__":
    # 使用示例
    csv_file = '常用机场代码.csv'
    output_file = 'route_data.csv'
    process_airport_codes(csv_file, output_file)
    # read_all_airport()
