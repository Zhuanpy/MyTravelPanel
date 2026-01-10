# -*- coding: utf-8 -*-
"""
设置操作员和业务员默认值为经办人
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
            # 更新 operator_id 和 operator_name 为经办人信息
            print("设置 operator 默认值为经办人...")
            db.session.execute(text("""
                UPDATE project_headers
                SET operator_id = staff_id,
                    operator_name = staff_name
                WHERE operator_name IS NULL AND staff_name IS NOT NULL
            """))

            # 更新 salesperson_id 和 salesperson_name 为经办人信息
            print("设置 salesperson 默认值为经办人...")
            db.session.execute(text("""
                UPDATE project_headers
                SET salesperson_id = staff_id,
                    salesperson_name = staff_name
                WHERE salesperson_name IS NULL AND staff_name IS NOT NULL
            """))

            db.session.commit()
            print("默认值设置完成！")

        except Exception as e:
            db.session.rollback()
            print(f"设置失败: {e}")
            raise

if __name__ == '__main__':
    run_migration()
