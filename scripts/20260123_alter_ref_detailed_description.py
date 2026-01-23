"""将 project_refs.detailed_description 字段从 VARCHAR(200) 改为 TEXT

原因：多段航班行程信息超过200字符限制
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    db.session.execute(db.text(
        "ALTER TABLE project_refs MODIFY COLUMN detailed_description TEXT NOT NULL COMMENT '详细描述'"
    ))
    db.session.commit()
    print("完成：detailed_description 字段已改为 TEXT 类型")
