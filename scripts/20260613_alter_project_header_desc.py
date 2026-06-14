"""将 project_headers.desc 字段改为 TEXT 类型

原因：
- 模型 ProjectHeader.desc 已声明为 db.Text，但实际数据库列仍是短 VARCHAR，二者不同步。
- REF 变更后会触发事件监听 _update_header_via_sql()，把项目下所有活跃 REF 的
  description 用 " / " 拼接后写回 desc；复制 REF 会让拼接结果越来越长，
  超过列宽即报错：DataError (1406, "Data too long for column 'desc'")。

修复：把列宽放开到 TEXT（约 64KB），与模型定义保持一致。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 改前先看一下当前列定义，便于核对
    before = db.session.execute(db.text(
        "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'project_headers' AND COLUMN_NAME = 'desc' "
        "AND TABLE_SCHEMA = DATABASE()"
    )).scalar()
    print(f"修改前 desc 列类型: {before}")

    # desc 在模型中可空（nullable 默认），保持可空
    db.session.execute(db.text(
        "ALTER TABLE project_headers MODIFY COLUMN `desc` TEXT COMMENT '项目描述'"
    ))
    db.session.commit()

    after = db.session.execute(db.text(
        "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'project_headers' AND COLUMN_NAME = 'desc' "
        "AND TABLE_SCHEMA = DATABASE()"
    )).scalar()
    print(f"修改后 desc 列类型: {after}")
    print("完成：project_headers.desc 字段已改为 TEXT 类型")
