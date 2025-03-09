from sqlalchemy import create_engine

import pandas as pd

# 设置显示所有列
pd.set_option('display.max_columns', None)


def original_airport_code_data():
    # 创建数据库连接
    engine = create_engine('mysql+pymysql://root:651748264Zz*@localhost/traveldata')

    # 使用SQL查询读取数据
    query = "SELECT * FROM airport_data"
    df = pd.read_sql(query, engine)
    df['机场三字码'] = df['机场三字码'].str.replace(' ', '', regex=False)
    df = df.drop_duplicates(subset=["机场三字码"])
    return df


def original_flight_timing_data():
    # 创建数据库连接
    engine = create_engine('mysql+pymysql://root:651748264Zz*@localhost/travelindustry')

    # 使用SQL查询读取数据
    query = "SELECT * FROM flight_schedule"
    df = pd.read_sql(query, engine)
    df['flight_number'] = df['flight_number'].str.replace(' ', '', regex=False)
    df = df.drop_duplicates(subset=["flight_number"])

    return df


if __name__ == '__main__':
    data = original_flight_timing_data()

    print(data)
