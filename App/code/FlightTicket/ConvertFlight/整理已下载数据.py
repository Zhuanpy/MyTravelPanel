import pandas as pd


def remove_duplicates_and_save(input_file, output_file):
    """
    读取 CSV 文件，去除重复数据并保存到新的 CSV 文件中。

    参数：
    input_file (str): 输入的 CSV 文件路径。
    output_file (str): 输出的 CSV 文件路径，将保存去重后的数据。
    """
    # 读取 CSV 文件到 DataFrame
    df = pd.read_csv(input_file)
    df_unique = df.drop_duplicates(subset=["Full Flight Number"]).reset_index(drop=True)
    # print(df_unique)
    # exit()
    # 保存去重后的数据到新的 CSV 文件
    df_unique.to_csv(output_file, index=False)
    print(f"去重后的数据已保存到 {output_file}")


# 使用示例
if __name__ == "__main__":
    input_file = "flight_timing.csv"
    output_file = "flight_timing-a.csv"
    remove_duplicates_and_save(input_file, output_file)
