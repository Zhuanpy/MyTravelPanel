# -*- coding: utf-8 -*-
"""
清理数据库里字面量字符串 "None"

背景:
    早期模板把可空字段写成 `{{ obj.field if obj else '' }}`，字段为 NULL 时
    Jinja 会把 Python 的 None 渲染成字面量 "None" 填进 input/textarea，
    用户一保存就把 "None" 这四个字母存回了库。之后凡是判断 `{% if obj.field %}`
    的地方都会当成有值，最终印到客户看到的发票 / 凭证 / 行程单上。

    典型现场: 酒店 REF 的 voucher 打印页出现 "Remarks / 备注  None"。

处理范围:
    默认只清 remarks 系列字段（列名含 remark），这是已定位的 bug 面。
    其它字符串列同样扫描，但**只报告不修改**，交由人工确认后用 --all 处理，
    避免误伤 "None" 确实是业务值的字段（比如 age_limit 填 None 表示不限）。

    清理动作: 该列可为空则置 NULL，否则置空串。只匹配去空白后完全等于
    None/none/NONE 的值，不做模糊匹配。

幂等: 清完再跑一次匹配 0 行，可安全重复执行（server_update.sh 会自动跑一次）。

运行方式:
    python scripts/20260729_clean_remarks_none.py              # 清 remarks 系列
    python scripts/20260729_clean_remarks_none.py --dry-run    # 只看不改
    python scripts/20260729_clean_remarks_none.py --all        # 连其它字符串列一起清
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import String, Text, inspect as sa_inspect

from App_new import create_app
from App_new.exts import db

# 去空白后等于这些值的才算脏数据
DIRTY_VALUES = ('None', 'none', 'NONE')


def _is_remarks_column(column):
    """是否属于 remarks 系列（已定位 bug 面，默认清理范围）"""
    return 'remark' in column.name.lower()


def _scan(table_name, column_name):
    """返回该列脏数据行数；表/列不存在等异常返回 None 表示跳过"""
    sql = 'SELECT COUNT(*) FROM `{t}` WHERE TRIM(`{c}`) IN :vals'.format(
        t=table_name, c=column_name)
    try:
        return db.session.execute(
            db.text(sql).bindparams(db.bindparam('vals', expanding=True)),
            {'vals': list(DIRTY_VALUES)}
        ).scalar()
    except Exception as exc:
        print('  跳过 {}.{}: {}'.format(table_name, column_name, exc))
        db.session.rollback()
        return None


def _clean(table_name, column_name, nullable):
    """把脏值置为 NULL（列不可空时置空串），返回影响行数"""
    new_value = 'NULL' if nullable else "''"
    sql = 'UPDATE `{t}` SET `{c}` = {v} WHERE TRIM(`{c}`) IN :vals'.format(
        t=table_name, c=column_name, v=new_value)
    result = db.session.execute(
        db.text(sql).bindparams(db.bindparam('vals', expanding=True)),
        {'vals': list(DIRTY_VALUES)}
    )
    return result.rowcount


def main():
    parser = argparse.ArgumentParser(description='清理数据库里字面量字符串 "None"')
    parser.add_argument('--dry-run', action='store_true',
                        help='只统计不修改')
    parser.add_argument('--all', action='store_true',
                        help='除 remarks 系列外，其它字符串列也一并清理')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        existing_tables = set(sa_inspect(db.engine).get_table_names())

        targets = []   # 本次要清理的列
        others = []    # 只报告不清理的列

        for table in db.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            for column in table.columns:
                if not isinstance(column.type, (String, Text)):
                    continue
                count = _scan(table.name, column.name)
                if not count:
                    continue
                entry = (table.name, column.name, column.nullable, count)
                if _is_remarks_column(column) or args.all:
                    targets.append(entry)
                else:
                    others.append(entry)

        if not targets and not others:
            print('OK: 没有发现字面量 "None"，无需处理')
            return

        if targets:
            print('\n=== 待清理 ({} 列) ==='.format(len(targets)))
            print('%-40s %-28s %-8s %s' % ('表', '字段', '可空', '行数'))
            for t, c, nullable, n in targets:
                print('%-40s %-28s %-8s %d' % (t, c, '是' if nullable else '否', n))
            print('小计 {} 行'.format(sum(x[3] for x in targets)))

        if others:
            print('\n=== 仅报告，未处理 ({} 列) ==='.format(len(others)))
            print('这些列同样存在字面量 "None"，但可能是业务真值，确认后用 --all 清理：')
            print('%-40s %-28s %s' % ('表', '字段', '行数'))
            for t, c, _nullable, n in others:
                print('%-40s %-28s %d' % (t, c, n))
            print('小计 {} 行'.format(sum(x[3] for x in others)))

        if args.dry_run:
            print('\n[dry-run] 未做任何修改')
            return

        if not targets:
            print('\n本次无需清理（remarks 系列干净）；其它列如需处理请加 --all')
            return

        try:
            total = 0
            for table_name, column_name, nullable, _count in targets:
                total += _clean(table_name, column_name, nullable)
            db.session.commit()
            print('\nOK: 已清理 {} 行'.format(total))
        except Exception as exc:
            db.session.rollback()
            print('\n失败: {}'.format(exc))
            # 非零退出，让 server_update.sh 不记录为成功、下次部署自动重试
            sys.exit(1)


if __name__ == '__main__':
    main()
