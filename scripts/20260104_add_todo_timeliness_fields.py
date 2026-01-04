# -*- coding: utf-8 -*-
"""
添加任务准时性跟踪字段到 todos 表

运行方式: python scripts/20260104_add_todo_timeliness_fields.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new.exts import db
from app_new import create_app
from sqlalchemy import text

def run_migration():
    """执行数据库迁移"""
    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'todos'
                AND COLUMN_NAME IN ('is_on_time', 'delay_days')
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # 添加 is_on_time 字段
            if 'is_on_time' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todos
                    ADD COLUMN is_on_time BOOLEAN DEFAULT NULL
                    COMMENT '任务是否准时完成: TRUE=准时, FALSE=延迟, NULL=未完成'
                """))
                print("已添加 is_on_time 字段")
            else:
                print("is_on_time 字段已存在，跳过")

            # 添加 delay_days 字段
            if 'delay_days' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE todos
                    ADD COLUMN delay_days INT DEFAULT 0
                    COMMENT '延迟天数（负数表示提前完成）'
                """))
                print("已添加 delay_days 字段")
            else:
                print("delay_days 字段已存在，跳过")

            db.session.commit()
            print("数据库迁移完成！")

            # 更新历史数据：计算已完成任务的准时性
            print("\n开始更新历史数据...")
            result = db.session.execute(text("""
                UPDATE todos
                SET is_on_time = CASE
                    WHEN due_date IS NULL THEN TRUE
                    WHEN completed_at <= due_date THEN TRUE
                    ELSE FALSE
                END,
                delay_days = CASE
                    WHEN due_date IS NULL THEN 0
                    ELSE DATEDIFF(completed_at, due_date)
                END
                WHERE is_completed = TRUE AND completed_at IS NOT NULL
            """))
            db.session.commit()
            print(f"已更新 {result.rowcount} 条历史任务记录")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {str(e)}")
            raise


if __name__ == '__main__':
    run_migration()
