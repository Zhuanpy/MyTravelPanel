# -*- coding: utf-8 -*-
"""
更新 journal_entries 表的 source_type 枚举，添加 operating_expense
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def update_enum():
    """更新 source_type 枚举"""

    sql = """
    ALTER TABLE project_journal_entries
    MODIFY COLUMN source_type ENUM('invoice', 'receipt', 'eo', 'manual', 'operating_expense')
    NOT NULL COMMENT '来源类型'
    """

    db.session.execute(text(sql))
    db.session.commit()
    print("source_type ENUM 更新成功!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("更新 source_type ENUM")
        print("=" * 50)
        update_enum()
