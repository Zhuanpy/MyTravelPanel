# -*- coding: utf-8 -*-
"""迁移：机票乘客表新增 baggage、seats 字段，并放宽 pnr 长度

背景：票号/PNR/行李额改为按乘客存储（每位乘客一套，全程通用）；
座位按 乘客×航段 区分，存为 seats（JSON 列表，按航段顺序）。

幂等：重复运行安全（已存在的列会跳过）。
运行：python scripts/20260628_passenger_ticketing_fields.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

TABLE = 'project_flight_passengers'


def _columns(conn):
    rows = conn.execute(text(f"SHOW COLUMNS FROM {TABLE}")).fetchall()
    return {r[0] for r in rows}


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            cols = _columns(conn)

            if 'baggage' not in cols:
                conn.execute(text(
                    f"ALTER TABLE {TABLE} ADD COLUMN baggage VARCHAR(50) NULL COMMENT '行李额'"))
                print("已新增列：baggage")
            else:
                print("跳过：baggage 已存在")

            if 'seats' not in cols:
                conn.execute(text(
                    f"ALTER TABLE {TABLE} ADD COLUMN seats TEXT NULL COMMENT '各航段座位号(JSON列表,按航段顺序)'"))
                print("已新增列：seats")
            else:
                print("跳过：seats 已存在")

            # 放宽 pnr 长度到 10（原为 6），与航段级 PNR 一致；幂等执行
            conn.execute(text(
                f"ALTER TABLE {TABLE} MODIFY COLUMN pnr VARCHAR(10) NULL COMMENT 'PNR编码'"))
            print("已确认 pnr 长度为 VARCHAR(10)")

        print("迁移完成。")


if __name__ == '__main__':
    main()
