"""REF 删除受阻诊断 / 清理（默认只读）

用途: 排查删除 REF 或删除项目时报
  (1451, 'Cannot delete or update a parent row: a foreign key constraint fails
   (`travelindustry`.`project_flight_passenger_segments`, CONSTRAINT ... FOREIGN KEY (`passenger_id`) ...)')

会打印:
  - 该 REF 下机票子表的行数（乘客 / 航段 / 乘客×航段格子）
  - 「错位格子」：格子的 passenger/segment 属于本 REF，但格子自己的 ref_id 不是本 REF
    （按 ref_id 批量清理会漏掉它们，正是 1451 的常见成因）
  - 其它会挡住删除的业务数据（EO / 预付款使用 / 签证 / 订单项 / 发票项 / 收款）
  - 相关外键的 ON DELETE 规则（判断是不是数据库级联触发的连锁删除）

运行方式:
    python scripts/tools/20260731_diagnose_ref_delete.py 4570
    python scripts/tools/20260731_diagnose_ref_delete.py 4570 --fix        # 只清理机票子表(含错位格子)
    python scripts/tools/20260731_diagnose_ref_delete.py --scan            # 全库扫描错位格子
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text

from App_new import create_app
from App_new.exts import db


def q(sql, **params):
    return db.session.execute(text(sql), params).fetchall()


def scalar(sql, **params):
    row = db.session.execute(text(sql), params).fetchone()
    return row[0] if row else 0


def show_fk_rules():
    print('=== 机票相关外键的 ON DELETE 规则 ===')
    rows = q("""
        SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME,
               k.REFERENCED_TABLE_NAME, r.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r
          ON r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
         AND r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
        WHERE k.CONSTRAINT_SCHEMA = DATABASE()
          AND k.TABLE_NAME IN ('project_flight_passengers','project_flight_segments',
                               'project_flight_passenger_segments')
        ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME
    """)
    for t, cname, col, ref_table, rule in rows:
        print('  %-38s %-42s %-13s -> %-32s ON DELETE %s'
              % (t, cname, col, ref_table, rule))
    print('')


def find_stray_cells(ref_id):
    """格子的乘客或航段属于本 REF，但格子自己的 ref_id 不是本 REF —— 按 ref_id 清理会漏掉"""
    return q("""
        SELECT c.id, c.ref_id, c.passenger_id, c.segment_id, p.ref_id, s.ref_id
        FROM project_flight_passenger_segments c
        LEFT JOIN project_flight_passengers p ON p.id = c.passenger_id
        LEFT JOIN project_flight_segments   s ON s.id = c.segment_id
        WHERE (p.ref_id = :r OR s.ref_id = :r) AND c.ref_id <> :r
    """, r=ref_id)


def diagnose(ref_id):
    row = q('SELECT id, ref_number, header_id, description FROM project_refs WHERE id = :r', r=ref_id)
    if not row:
        print('❌ REF %s 不存在' % ref_id)
        return None
    _id, ref_number, header_id, desc = row[0]
    print('=== REF %s (%s)  项目header_id=%s ===' % (_id, ref_number, header_id))
    print('    描述: %s' % desc)
    print('')

    print('=== 机票子表 ===')
    pax = scalar('SELECT COUNT(*) FROM project_flight_passengers WHERE ref_id = :r', r=ref_id)
    seg = scalar('SELECT COUNT(*) FROM project_flight_segments WHERE ref_id = :r', r=ref_id)
    cell = scalar('SELECT COUNT(*) FROM project_flight_passenger_segments WHERE ref_id = :r', r=ref_id)
    print('  乘客 project_flight_passengers        : %s' % pax)
    print('  航段 project_flight_segments          : %s' % seg)
    print('  格子 project_flight_passenger_segments: %s（ref_id 匹配的）' % cell)

    stray = find_stray_cells(ref_id)
    print('  ❗错位格子（ref_id 对不上，批量清理会漏掉）: %s' % len(stray))
    for cid, c_ref, pid, sid, p_ref, s_ref in stray:
        print('     cell id=%s cell.ref_id=%s passenger_id=%s(ref=%s) segment_id=%s(ref=%s)'
              % (cid, c_ref, pid, p_ref, sid, s_ref))
    print('')

    print('=== 其它会挡住删除的业务数据 ===')
    checks = [
        ('EO project_eos', 'SELECT COUNT(*) FROM project_eos WHERE ref_id = :r'),
        ('预付款使用 prepayment_usages', 'SELECT COUNT(*) FROM prepayment_usages WHERE ref_id = :r'),
        ('签证项目 visa_projects', 'SELECT COUNT(*) FROM visa_projects WHERE ref_id = :r'),
        ('订单项 ref_order_items', 'SELECT COUNT(*) FROM ref_order_items WHERE ref_id = :r'),
    ]
    for label, sql in checks:
        try:
            print('  %-34s %s' % (label, scalar(sql, r=ref_id)))
        except Exception as e:
            db.session.rollback()
            print('  %-34s 查询失败(表可能不存在): %s' % (label, e))
    print('')
    return stray


def scan_all():
    print('=== 全库扫描：ref_id 与所属乘客对不上的格子 ===')
    rows = q("""
        SELECT c.id, c.ref_id, c.passenger_id, p.ref_id, c.segment_id, s.ref_id
        FROM project_flight_passenger_segments c
        LEFT JOIN project_flight_passengers p ON p.id = c.passenger_id
        LEFT JOIN project_flight_segments   s ON s.id = c.segment_id
        WHERE p.id IS NULL OR s.id IS NULL OR c.ref_id <> p.ref_id OR c.ref_id <> s.ref_id
        ORDER BY c.id
    """)
    if not rows:
        print('  ✅ 没有发现错位/孤儿格子')
        return []
    for cid, c_ref, pid, p_ref, sid, s_ref in rows:
        print('  cell id=%s ref_id=%s | passenger %s(ref=%s) | segment %s(ref=%s)'
              % (cid, c_ref, pid, p_ref, sid, s_ref))
    print('  合计 %s 行' % len(rows))
    return rows


def fix(ref_id):
    """清理该 REF 的机票子表：先按 ref_id 删格子，再补删错位格子，最后删乘客/航段"""
    n_cell = db.session.execute(
        text('DELETE FROM project_flight_passenger_segments WHERE ref_id = :r'), {'r': ref_id}).rowcount
    n_stray = db.session.execute(text("""
        DELETE c FROM project_flight_passenger_segments c
        LEFT JOIN project_flight_passengers p ON p.id = c.passenger_id
        LEFT JOIN project_flight_segments   s ON s.id = c.segment_id
        WHERE p.ref_id = :r OR s.ref_id = :r
    """), {'r': ref_id}).rowcount
    n_pax = db.session.execute(
        text('DELETE FROM project_flight_passengers WHERE ref_id = :r'), {'r': ref_id}).rowcount
    n_seg = db.session.execute(
        text('DELETE FROM project_flight_segments WHERE ref_id = :r'), {'r': ref_id}).rowcount
    db.session.commit()
    print('✅ 已清理: 格子 %s + 错位格子 %s，乘客 %s，航段 %s' % (n_cell, n_stray, n_pax, n_seg))
    print('   现在可以在页面上重新删除该 REF')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ref_id', nargs='?', type=int, help='要诊断的 REF ID')
    parser.add_argument('--fix', action='store_true', help='清理该 REF 的机票子表（含错位格子）')
    parser.add_argument('--scan', action='store_true', help='全库扫描错位/孤儿格子')
    args = parser.parse_args()

    if not args.ref_id and not args.scan:
        parser.error('请给出 ref_id，或使用 --scan')

    app = create_app()
    with app.app_context():
        show_fk_rules()
        if args.scan:
            scan_all()
            return
        stray = diagnose(args.ref_id)
        if stray is None:
            return
        if args.fix:
            fix(args.ref_id)
        else:
            print('提示: 加 --fix 可清理该 REF 的机票子表（不会删 REF 本身，也不动 EO/收款等业务数据）')


if __name__ == '__main__':
    main()
