# -*- coding: utf-8 -*-
"""
更新操作员和业务员字段支持多选
- 删除旧的单值字段
- 添加新的多值字段（逗号分隔）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

def run_migration():
    """执行迁移"""
    with app.app_context():
        try:
            # 检查新字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'project_headers'
                AND COLUMN_NAME = 'operator_ids'
            """))

            if result.fetchone():
                print("字段 operator_ids 已存在，跳过迁移")
                return

            # 先备份旧数据（如果有的话）
            print("备份旧数据...")
            db.session.execute(text("""
                UPDATE project_headers
                SET operator_ids = CAST(operator_id AS CHAR),
                    operator_names = operator_name,
                    salesperson_ids = CAST(salesperson_id AS CHAR),
                    salesperson_names = salesperson_name
                WHERE operator_id IS NOT NULL OR salesperson_id IS NOT NULL
            """))

        except Exception as e:
            print(f"备份步骤跳过: {e}")

        try:
            # 删除旧字段
            print("删除旧字段 operator_id...")
            try:
                db.session.execute(text("ALTER TABLE project_headers DROP COLUMN operator_id"))
            except:
                pass

            print("删除旧字段 operator_name...")
            try:
                db.session.execute(text("ALTER TABLE project_headers DROP COLUMN operator_name"))
            except:
                pass

            print("删除旧字段 salesperson_id...")
            try:
                db.session.execute(text("ALTER TABLE project_headers DROP COLUMN salesperson_id"))
            except:
                pass

            print("删除旧字段 salesperson_name...")
            try:
                db.session.execute(text("ALTER TABLE project_headers DROP COLUMN salesperson_name"))
            except:
                pass

            # 检查新字段是否存在，如果不存在则添加
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'project_headers'
                AND COLUMN_NAME = 'operator_ids'
            """))

            if not result.fetchone():
                print("添加 operator_ids 字段...")
                db.session.execute(text("""
                    ALTER TABLE project_headers
                    ADD COLUMN operator_ids VARCHAR(200) NULL
                    COMMENT '操作员ID列表(逗号分隔)'
                """))

                print("添加 operator_names 字段...")
                db.session.execute(text("""
                    ALTER TABLE project_headers
                    ADD COLUMN operator_names VARCHAR(500) NULL
                    COMMENT '操作员姓名列表(逗号分隔)'
                """))

                print("添加 salesperson_ids 字段...")
                db.session.execute(text("""
                    ALTER TABLE project_headers
                    ADD COLUMN salesperson_ids VARCHAR(200) NULL
                    COMMENT '业务员ID列表(逗号分隔)'
                """))

                print("添加 salesperson_names 字段...")
                db.session.execute(text("""
                    ALTER TABLE project_headers
                    ADD COLUMN salesperson_names VARCHAR(500) NULL
                    COMMENT '业务员姓名列表(逗号分隔)'
                """))

            # 设置默认值为经办人
            print("设置默认值为经办人...")
            db.session.execute(text("""
                UPDATE project_headers
                SET operator_ids = CAST(staff_id AS CHAR),
                    operator_names = staff_name,
                    salesperson_ids = CAST(staff_id AS CHAR),
                    salesperson_names = staff_name
                WHERE (operator_names IS NULL OR operator_names = '')
                AND staff_name IS NOT NULL
            """))

            db.session.commit()
            print("迁移完成！")

        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {e}")
            raise

if __name__ == '__main__':
    run_migration()
