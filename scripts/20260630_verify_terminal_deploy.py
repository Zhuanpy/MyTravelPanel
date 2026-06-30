# -*- coding: utf-8 -*-
"""
验证航站楼字段迁移 + 航段局部更新接口是否已部署生效

检查项:
1. project_flight_segments.departure_terminal / arrival_terminal 是否为 VARCHAR(50)
2. 两个新接口是否已注册:
   - GET  /projects/ref/flight/<ref_id>/segments
   - POST /projects/ref/flight/segment/<segment_id>/update

运行方式: python scripts/20260630_verify_terminal_deploy.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

all_ok = True

with app.app_context():
    # ---- 1. 检查航站楼列长度 ----
    print('=' * 50)
    print('1. 航站楼字段长度检查')
    print('=' * 50)
    try:
        rows = db.session.execute(db.text(
            "SHOW COLUMNS FROM project_flight_segments LIKE '%terminal%'"
        )).fetchall()
        if not rows:
            print('  ✗ 未找到 terminal 字段，请检查表是否存在')
            all_ok = False
        for r in rows:
            field, col_type = r[0], r[1]
            ok = 'varchar(50)' in str(col_type).lower()
            mark = '✓' if ok else '✗'
            print(f'  {mark} {field}: {col_type}')
            if not ok:
                all_ok = False
    except Exception as e:
        print(f'  ✗ 查询失败: {e}')
        all_ok = False

    # ---- 2. 检查新接口是否注册 ----
    print()
    print('=' * 50)
    print('2. 新接口注册检查')
    print('=' * 50)
    expected = [
        'flight/segment',          # 局部更新接口片段
        'flight',                  # 列表接口片段（配合 segments 判断）
    ]
    rules = [str(r.rule) for r in app.url_map.iter_rules()]
    found_list = [s for s in rules if s.endswith('/segments') and 'flight' in s]
    found_update = [s for s in rules if 'flight/segment/' in s]

    if found_list:
        print(f'  ✓ 列表接口: {found_list[0]}')
    else:
        print('  ✗ 未找到航段列表接口 (.../flight/<ref_id>/segments)')
        all_ok = False

    if found_update:
        print(f'  ✓ 更新接口: {found_update[0]}')
    else:
        print('  ✗ 未找到航段更新接口 (.../flight/segment/<id>/update)')
        all_ok = False

# ---- 汇总 ----
print()
print('=' * 50)
if all_ok:
    print('结果: ✓ 全部通过，部署已生效')
    sys.exit(0)
else:
    print('结果: ✗ 有检查项未通过，见上方 ✗ 标记')
    sys.exit(1)
