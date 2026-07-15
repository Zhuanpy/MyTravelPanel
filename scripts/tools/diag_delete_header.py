"""诊断：删除项目失败的真实数据库报错

用法: python scripts/tools/diag_delete_header.py <header_id>

- 统计该项目下各子表的记录数
- 在事务中真实执行一次删除，捕获异常后 rollback（不会真的删数据）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def main():
    header_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3332

    app = create_app()
    with app.app_context():
        conn = db.session

        # 1. 该项目关联的 ref_id / eo_id / receipt_id / invoice_id
        ref_ids = [r[0] for r in conn.execute(
            text('SELECT id FROM project_refs WHERE header_id = :h'), {'h': header_id})]
        eo_ids = []
        if ref_ids:
            eo_ids = [r[0] for r in conn.execute(
                text('SELECT id FROM project_eos WHERE ref_id IN :refs').bindparams(
                    __import__('sqlalchemy').bindparam('refs', expanding=True)), {'refs': ref_ids})]

        print(f'=== 项目 {header_id} ===')
        print(f'REF: {ref_ids}')
        print(f'EO : {eo_ids}')

        # 2. 各子表记录数
        checks = [
            ('project_members', 'header_id', [header_id]),
            ('project_invoices', 'header_id', [header_id]),
            ('project_receipts', 'header_id', [header_id]),
            ('project_refunds', 'header_id', [header_id]),
            ('project_journal_entries', 'header_id', [header_id]),
            ('flight_orders', 'project_header_id', [header_id]),
            ('visa_projects', 'header_id', [header_id]),
            ('project_files', 'header_id', [header_id]),
            ('project_reminders', 'header_id', [header_id]),
            ('project_emails', 'header_id', [header_id]),
            ('project_flight_segments', 'ref_id', ref_ids),
            ('project_flight_passengers', 'ref_id', ref_ids),
            ('project_flight_passenger_segments', 'ref_id', ref_ids),
            ('ref_order_items', 'ref_id', ref_ids),
            ('bank_transactions', 'ref_id', ref_ids),
            ('prepayment_usages', 'ref_id', ref_ids),
            ('bank_transactions', 'eo_id', eo_ids),
            ('prepayment_usages', 'eo_id', eo_ids),
            ('supplier_statement_items', 'eo_id', eo_ids),
        ]
        print('\n=== 子表记录数（>0 的才可能挡住删除）===')
        for table, col, ids in checks:
            if not ids:
                continue
            try:
                placeholders = ','.join(str(int(i)) for i in ids)
                n = conn.execute(text(
                    f'SELECT COUNT(*) FROM {table} WHERE {col} IN ({placeholders})')).scalar()
                if n:
                    print(f'  {table}.{col}: {n}')
            except Exception as e:
                print(f'  {table}.{col}: [查询失败] {e}')

        # 3. 实际数据库里 project_headers / project_refs 被哪些外键引用（含 ON DELETE 规则）
        print('\n=== 数据库实际外键（引用 project_headers / project_refs / project_eos）===')
        rows = conn.execute(text("""
            SELECT k.TABLE_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, r.DELETE_RULE
            FROM information_schema.KEY_COLUMN_USAGE k
            JOIN information_schema.REFERENTIAL_CONSTRAINTS r
              ON r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
             AND r.CONSTRAINT_SCHEMA = k.TABLE_SCHEMA
            WHERE k.TABLE_SCHEMA = DATABASE()
              AND k.REFERENCED_TABLE_NAME IN
                  ('project_headers','project_refs','project_eos','project_invoices','project_receipts')
            ORDER BY k.REFERENCED_TABLE_NAME, k.TABLE_NAME
        """))
        for t, c, ref_t, rule in rows:
            print(f'  {t}.{c} -> {ref_t}  ON DELETE {rule}')

        # 4. 真实走一遍现有删除逻辑，捕获报错后回滚
        print('\n=== 试删（结束后 rollback，不会真删）===')
        try:
            from App_new.business.projects.models.project import ProjectHeader
            from App_new.business.projects.models.invoice import ProjectInvoice, InvoiceItem
            from App_new.business.projects.models.receipt import ProjectReceipt
            from App_new.business.projects.models.ref import ProjectRef
            from App_new.business.projects.models.eo import ProjectEO

            header = ProjectHeader.query.get(header_id)
            if not header:
                print('  项目不存在')
                return

            for invoice in ProjectInvoice.query.filter_by(header_id=header_id).all():
                InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
                db.session.delete(invoice)
            for receipt in ProjectReceipt.query.filter_by(header_id=header_id).all():
                db.session.delete(receipt)
            for ref in ProjectRef.query.filter_by(header_id=header_id).all():
                for eo in ProjectEO.query.filter_by(ref_id=ref.id).all():
                    db.session.delete(eo)
                db.session.delete(ref)
            db.session.delete(header)
            db.session.flush()  # 只 flush，不 commit
            print('  [OK] 现有删除逻辑没有报错（flush 通过）')
        except Exception as e:
            print(f'  [FAIL] {type(e).__name__}')
            print(f'  {e}')
        finally:
            db.session.rollback()
            print('  已 rollback')


if __name__ == '__main__':
    main()