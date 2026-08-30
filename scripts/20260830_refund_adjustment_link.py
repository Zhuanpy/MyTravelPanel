"""退款单记录它生成的「退款调整单」

退款单只是凭证，不进账。真正让「供应商退回 − 退给客户」这笔差额进到项目利润
和分成里的，是一条 refund 类型的 REF。原先这一串全靠人手工做，漏一步就静默
卡住结算，而且界面上根本选不到 refund 类型。

新增字段：
- adjustment_header_id  退款调整单所在项目ID（原单已结算时会另开一张并关联回主单）
- adjustment_ref_id     退款调整 REF 的 ID（用于判断是否已生成、避免重复）

两个外键都是 ON DELETE SET NULL：调整单做错了要能删掉重做，普通外键会让
「删除 REF」报 1451，删不掉也重建不了。脚本会顺带修复已存在但缺该规则的外键。

运行方式: python scripts/20260830_refund_adjustment_link.py

前置：需先执行 20260829_refund_settlement_support.py（提供 refund 业务类型与
related_header_id）。幂等，可重复执行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from App_new import create_app
from App_new.exts import db

app = create_app()

NEW_COLUMNS = [
    ('adjustment_header_id', 'project_headers', '退款调整单所在项目ID'),
    ('adjustment_ref_id', 'project_refs', '退款调整REF的ID'),
]


def main():
    with app.app_context():
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table('project_refunds'):
                print('[SKIP] 表 project_refunds 不存在')
                return

            existing = {c['name'] for c in inspector.get_columns('project_refunds')}
            added = 0
            for name, ref_table, comment in NEW_COLUMNS:
                if name not in existing:
                    conn.execute(text(
                        "ALTER TABLE project_refunds ADD COLUMN `%s` INT NULL COMMENT '%s'"
                        % (name, comment)
                    ))
                    existing.add(name)
                    added += 1
                    print('[OK] 已添加 %s' % name)
                else:
                    print('[SKIP] %s 已存在' % name)

                if not inspect(conn).has_table(ref_table):
                    continue

                # 外键必须是 ON DELETE SET NULL：调整单是可以删的（做错了要能重做），
                # 普通外键会让「删除 REF」直接报 1451，删不掉也重建不了。
                # 删掉调整单后这里自动置空，退款单就回到「未生成」，可以重新生成。
                fk_name = 'fk_refund_%s' % name
                rule = conn.execute(text(
                    "SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'project_refunds' "
                    "AND CONSTRAINT_NAME = :fk"), {'fk': fk_name}).scalar()

                if rule == 'SET NULL':
                    print('[SKIP] 外键 %s 已是 ON DELETE SET NULL' % fk_name)
                    continue
                if rule is not None:
                    conn.execute(text(
                        "ALTER TABLE project_refunds DROP FOREIGN KEY `%s`" % fk_name))
                    print('[FIX] 旧外键 %s（%s）已删除，准备重建' % (fk_name, rule))

                conn.execute(text(
                    "ALTER TABLE project_refunds ADD CONSTRAINT `%s` "
                    "FOREIGN KEY (`%s`) REFERENCES `%s`(id) ON DELETE SET NULL"
                    % (fk_name, name, ref_table)
                ))
                print('[OK] 外键 %s -> %s ON DELETE SET NULL' % (fk_name, ref_table))

            # 前置检查：没有 refund 业务类型的话，生成调整单会直接失败
            if inspect(conn).has_table('business_types'):
                has_type = conn.execute(text(
                    "SELECT COUNT(*) FROM business_types WHERE code = 'refund'"
                )).scalar()
                if not has_type:
                    print('[WARN] 缺少「退款调整」业务类型，'
                          '请先执行 scripts/20260829_refund_settlement_support.py')

            print('\n新增 %d 列，迁移完成。' % added)


if __name__ == '__main__':
    main()
