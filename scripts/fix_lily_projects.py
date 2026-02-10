# -*- coding: utf-8 -*-
"""修复 H719/H309 的经办人和操作员为 Lily"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Lily 的用户ID
    LILY_ID = 24
    LILY_NAME = 'Lily'

    # H719: 经办人改 Lily，操作员改 Lily（业务员已经是 Lily）
    db.session.execute(text(
        "UPDATE project_headers SET staff_id=:uid, staff_name=:name, "
        "operator_ids=:uid_str, operator_names=:name "
        "WHERE hid='H719'"
    ), {'uid': LILY_ID, 'uid_str': str(LILY_ID), 'name': LILY_NAME})
    print("H719: 经办人→Lily, 操作员→Lily")

    # H309: 经办人改 Lily（操作员和业务员已经是 Lily）
    db.session.execute(text(
        "UPDATE project_headers SET staff_id=:uid, staff_name=:name "
        "WHERE hid='H309'"
    ), {'uid': LILY_ID, 'name': LILY_NAME})
    print("H309: 经办人→Lily")

    db.session.commit()
    print("修复完成！")
