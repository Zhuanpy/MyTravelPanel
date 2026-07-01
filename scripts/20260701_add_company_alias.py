"""
给 customer_companies 增加 alias（简称/别名）列

用途: 让公司搜索 API 能按缩写命中（如 QJEC、CHB），
      与 company_code（存 UEN 注册号）分开，避免覆盖真实注册号。

幂等: 列已存在则跳过，可重复运行。
运行方式: python scripts/20260701_add_company_alias.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        exists = db.session.execute(db.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'customer_companies' "
            "AND COLUMN_NAME = 'alias'"
        )).scalar()

        if exists:
            print('SKIP: customer_companies.alias 已存在，无需迁移')
        else:
            db.session.execute(db.text(
                "ALTER TABLE customer_companies "
                "ADD COLUMN alias VARCHAR(50) NULL COMMENT '简称/别名（供搜索）' "
                "AFTER company_code"
            ))
            db.session.commit()
            print('OK: customer_companies.alias 已添加 (VARCHAR(50))')
    except Exception as e:
        db.session.rollback()
        print(f'失败: {e}')
        # 非零退出，让部署脚本不记录为成功、下次自动重试
        sys.exit(1)
