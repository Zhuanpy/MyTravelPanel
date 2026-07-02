"""
将韩国签证坐标表 (资源/签证/韩国签证/source/坐标列表.xls) 导入 MySQL。

- 创建 visa_form_coordinates 表(若不存在)
- 以 country='korea' 导入坐标数据
- 幂等:重复运行会先清空 korea 旧数据再导入

运行方式: python scripts/20260629_import_korea_visa_coordinates.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from App_new import create_app
from App_new.exts import db
from App_new.business.visa.models import VisaFormCoordinate
from App_new.config import Config

COUNTRY = 'korea'

app = create_app()

with app.app_context():
    # 1. 建表(仅创建尚不存在的表)
    db.create_all()

    # 2. 定位 xls
    xls_path = os.path.join(Config.PROJECT_ROOT, '资源', '签证', '韩国签证', 'source', '坐标列表.xls')
    if not os.path.exists(xls_path):
        print(f'失败: 坐标文件不存在: {xls_path}')
        sys.exit(1)

    df = pd.read_excel(xls_path, sheet_name='Sheet1')
    # 过滤掉分隔空行(PAGE 为空)
    df = df[df['PAGE'].notna()].copy()

    try:
        # 3. 清空旧的 korea 数据(幂等)
        deleted = VisaFormCoordinate.query.filter_by(country=COUNTRY).delete()
        print(f'清除旧数据 {deleted} 条')

        # 4. 逐行导入
        imported = 0
        for _, row in df.iterrows():
            seq = str(row['坐标序列']).strip()
            if not seq or seq.lower() == 'nan':
                continue
            coord = VisaFormCoordinate(
                country=COUNTRY,
                page=str(row['PAGE']).strip(),
                seq=seq,
                coord_x=int(row['坐标X']),
                coord_y=int(row['坐标Y']),
                label=(str(row['坐标说明']).strip() if pd.notna(row['坐标说明']) else None),
                coord_type=(str(row['坐标类型']).strip() if pd.notna(row['坐标类型']) else None),
                type_note=(str(row['类型说明']).strip() if pd.notna(row['类型说明']) else None),
            )
            db.session.add(coord)
            imported += 1

        db.session.commit()
        print(f'OK: 已导入 {imported} 条韩国签证坐标到 visa_form_coordinates')
    except Exception as e:
        db.session.rollback()
        print(f'失败: {e}')
        sys.exit(1)
