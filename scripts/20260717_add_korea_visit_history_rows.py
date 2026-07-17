"""
为韩国签证「8.6 历史访问韩国」表格补第 2~5 行的填表坐标。

背景:
- 表格上这张表有 5 行(方문목적 Purpose of Visit / 방문기간 Period of Stay),
  母版 FormSample.xls 只给了第 1 行(8.6-2-1 / 8.6-2-2),坐标库里也只有这 1 行。
- 字段结构由代码补齐(见 visa_project.py 的 _KOREA_EXTRA_FIELDS),
  坐标由本脚本补进 visa_form_coordinates。

坐标怎么来的:
- 量 资源/签证/韩国签证/source/Form-page-3.jpg 的表格横线,
  5 个数据行的分隔线在 y=1968/2045/2122/2199/2276/2352,行高恒为 77px。
- 第 1 行文字已标定在 y=1995(库里现有值),故第 N 行 = 1995 + (N-1)*77。
- X 沿用第 1 行:目的 200,日期 1240。

幂等: 按 (country, seq) 存在则更新坐标,不存在则新增,可重复运行。

注意: 本脚本必须排在 20260629_import_korea_visa_coordinates.py 之后运行
(文件名日期已保证)。那个脚本在 坐标列表.xls 存在时会清空并重导 korea 坐标,
把本脚本加的行冲掉;部署按文件名顺序跑,跑完本脚本即可恢复。

运行方式: python scripts/20260717_add_korea_visit_history_rows.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.visa.models import VisaFormCoordinate

COUNTRY = 'korea'
PAGE = 'PAGE03'

FIRST_ROW_Y = 1995   # 第 1 行(8.6-2-*)文字 Y,与库中现有值一致
ROW_PITCH = 77       # 表格行高,量自 Form-page-3.jpg 的横线间距
X_PURPOSE = 200      # 目的列 X,沿用第 1 行
X_PERIOD = 1240      # 日期列 X,沿用第 1 行

# 第 N 次访问记录 → seq 8.6-(N+1)-1 / 8.6-(N+1)-2
ROWS = []
for n in range(2, 6):
    y = FIRST_ROW_Y + (n - 1) * ROW_PITCH
    ROWS.append((f'8.6-{n + 1}-1', X_PURPOSE, y, f'入境韩国目的{n}'))
    ROWS.append((f'8.6-{n + 1}-2', X_PERIOD, y, f'入境和出境韩国日期{n}'))

app = create_app()

with app.app_context():
    db.create_all()

    added, updated = 0, 0
    try:
        for seq, x, y, label in ROWS:
            row = VisaFormCoordinate.query.filter_by(country=COUNTRY, seq=seq).first()
            if row:
                row.page, row.coord_x, row.coord_y = PAGE, x, y
                row.label, row.coord_type = label, '填写'
                updated += 1
                print(f'更新 {seq}: ({x}, {y}) {label}')
            else:
                db.session.add(VisaFormCoordinate(
                    country=COUNTRY, page=PAGE, seq=seq,
                    coord_x=x, coord_y=y, label=label, coord_type='填写',
                ))
                added += 1
                print(f'新增 {seq}: ({x}, {y}) {label}')
        db.session.commit()
        print(f'完成: 新增 {added} 条, 更新 {updated} 条')
    except Exception as e:
        db.session.rollback()
        print(f'失败,已回滚: {e}')
        sys.exit(1)
