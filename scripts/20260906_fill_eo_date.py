# -*- coding: utf-8 -*-
"""回填 project_eos.eo_date

建单的四个入口（EO 表单创建、快速创建、CSV 导入 x2）都没填过 eo_date，
线上 716 条里 656 条是 NULL。下游只好到处兜底：

    App_new/finance/routes/reconciliation_routes.py 里按 EO 日期筛选的地方，
    每一处都写成「eo_date >= X  OR  (eo_date IS NULL AND created_at >= X)」

这个脚本按同一个口径把历史数据补上：eo_date = DATE(created_at)。
补完之后那些兜底分支只是走不到，结果不会变。

建单侧的修复在 App_new/business/projects/models/eo.py 的 __init__ 里，
以后新建的 EO 不会再是 NULL。

运行方式: python scripts/20260906_fill_eo_date.py

幂等，可重复执行（只补 NULL，不动已有值）。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()

TABLE = 'project_eos'


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(TABLE):
                print(f'[跳过] 表 {TABLE} 不存在')
                return

            before = conn.execute(text(
                f'SELECT COUNT(*) FROM {TABLE} WHERE eo_date IS NULL'
            )).scalar()
            if not before:
                print(f'[已完成] {TABLE}.eo_date 没有 NULL')
                return

            filled = conn.execute(text(
                f'UPDATE {TABLE} SET eo_date = DATE(created_at) '
                f'WHERE eo_date IS NULL AND created_at IS NOT NULL'
            )).rowcount

            # created_at 也为空的（理论上不存在，created_at 有默认值）单独报出来，
            # 不猜日期 —— 猜错会把这单算进错误的会计期间
            orphan = conn.execute(text(
                f'SELECT id, eo_number FROM {TABLE} WHERE eo_date IS NULL LIMIT 20'
            )).fetchall()

            print(f'[回填] {filled} 条 eo_date 已按 created_at 补上（原有 {before} 条 NULL）')
            if orphan:
                print(f'[待处理] {len(orphan)} 条 created_at 也为空，需人工确认日期：')
                for row in orphan:
                    print(f'    EO id={row[0]} {row[1]}')


if __name__ == '__main__':
    main()
