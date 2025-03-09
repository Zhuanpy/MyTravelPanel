from sqlalchemy import create_engine

import pandas as pd

# 设置显示所有列
pd.set_option('display.max_columns', None)


def process_and_store_airport_data(csv_file, db_url, table_name):
    # 读取 CSV 数据
    data = pd.read_csv(csv_file, encoding="utf-8", header=None)

    # 选择所需的列，并删除重复的机场三字码
    data = data[[1, 0, 3, 4]]
    data = data.drop_duplicates(subset=[1]).reset_index(drop=True)

    # 填充空的英文名称
    data[3] = data[3].fillna(data[0])

    # 重命名列
    columns = ["机场三字码", "城市名", "机场名称", "英文名称"]
    data.columns = columns

    # 删除三字码为空的数据
    data = data.dropna(subset=['机场三字码'])

    # 删除指定机场三字码（例如 KTD 和 KTR）
    data = data[~data["机场三字码"].isin(['KTD', 'KTR'])].reset_index(drop=True)

    # 建立 MySQL 数据库连接
    engine = create_engine(db_url)

    # 将数据写入 MySQL 表
    data.to_sql(name=table_name, con=engine, if_exists='replace', index=False)

    print(f"数据已成功写入到表 {table_name}")


def store_flight_timing(csv_file, db_url, table_name):
    # 读取 CSV 数据
    data = pd.read_csv(csv_file, encoding="utf-8")

    # 选择所需的列，并删除重复的机场三字码
    data["起始时间"] = data["Departure Time"] + " " + data["Arrival Time"]
    data["起始时间"] = data["起始时间"].str.replace(':', '')

    # 重命名列
    columns = ["Full Flight Number", "Airline IATA", "Flight Number", "Route IATA", "起始时间"]
    data = data[columns]

    columns = ["航班ID", "航司", "航班号", "起始城市", "起始时间"]

    data.columns = columns
    data = data.drop_duplicates(subset=["航班ID"]).reset_index(drop=True)

    # 建立 MySQL 数据库连接
    engine = create_engine(db_url)

    # 将数据追加到 MySQL 表格
    data.to_sql(name=table_name, con=engine, if_exists='replace', index=False)

    print(f"数据已成功追加到表 {table_name}")


# 如果需要处理主键冲突并进行更新，可以使用 SQLAlchemy 的 merge 方式进行 upsert
def upsert_flight_data(csv_file, db_url, table_name):
    # 读取 CSV 数据
    data = pd.read_csv(csv_file, encoding="utf-8")

    # 同样进行数据清理和列重命名
    data["起始时间"] = data["Departure Time"] + " " + data["Arrival Time"]
    data["起始时间"] = data["起始时间"].str.replace(':', '')

    columns = ["Full Flight Number", "Airline IATA", "Flight Number", "Route IATA", "起始时间"]
    data = data[columns]

    columns = ["航班ID", "航司", "航班号", "起始城市", "起始时间"]
    data.columns = columns
    data = data.drop_duplicates(subset=["航班ID"]).reset_index(drop=True)

    # 建立 MySQL 数据库连接
    engine = create_engine(db_url)

    # 从数据库中读取已存在的航班数据
    existing_data_query = f"SELECT 航班ID FROM {table_name}"
    existing_data = pd.read_sql(existing_data_query, con=engine)

    # 筛选出 CSV 文件中不存在于数据库的航班ID
    new_data = data[~data["航班ID"].isin(existing_data["航班ID"])].dropna(subset=["航班号"])

    # 只插入新的航班数据
    if not new_data.empty:
        connection = engine.connect()

        for index, row in new_data.iterrows():
            # 通过 SQL 实现 upsert 操作
            try:
                upsert_sql = f"""
                INSERT INTO {table_name} (航班ID, 航司, 航班号, 起始城市, 起始时间)
                VALUES ('{row["航班ID"]}', '{row["航司"]}', '{row["航班号"]}', '{row["起始城市"]}', '{row["起始时间"]}')
                ON DUPLICATE KEY UPDATE 
                航司=VALUES(航司), 
                航班号=VALUES(航班号), 
                起始城市=VALUES(起始城市), 
                起始时间=VALUES(起始时间)
                """
                connection.execute(upsert_sql)

            except Exception as e:
                print(f"在插入{row}或更新数据时发生错误: {e}")

        connection.close()
        print(f"数据已成功 upsert 到表 {table_name}")
    else:
        print("没有新数据需要插入或更新。")


# 示例使用
if __name__ == "__main__":
    csv_file = "flight_timing.csv"
    db_url = "mysql+pymysql://root:651748264Zz*@localhost/traveldata"
    table_name = "flight_timing_data"

    upsert_flight_data(csv_file, db_url, table_name)
