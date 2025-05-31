import pandas as pd
from sqlalchemy import create_engine
from config import Config
import os

def import_visalinks_from_csv(csv_path = r'E:\DATA\visalinks.csv'):
    try:
        # 创建数据库连接
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

        # 读取CSV文件
        df = pd.read_csv(csv_path)
        
        # 如果CSV中包含id列，但我们不想导入（因为是自增的），就删除它
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        
        # 将数据导入到数据库
        df.to_sql('visalinks', engine, if_exists='append', index=False)
        
        print(f"成功导入 {len(df)} 条记录到 visalinks 表")
        
    except Exception as e:
        print(f"导入过程中发生错误: {str(e)}")

if __name__ == "__main__":
    import_visalinks_from_csv() 