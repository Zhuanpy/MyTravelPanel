"""
创建签证填表模板表 visa_form_templates。

- 把一份填好的签证表存成模板，新项目可套用相同字段
- 按 visa_category(japan/korea) 隔离
- 幂等：仅创建尚不存在的表

运行方式: python scripts/20260702_add_visa_form_templates.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.visa.models import VisaFormTemplate  # noqa: F401

app = create_app()

with app.app_context():
    db.create_all()
    from sqlalchemy import inspect
    if inspect(db.engine).has_table('visa_form_templates'):
        print('OK: 表 visa_form_templates 已就绪')
    else:
        print('失败: 表 visa_form_templates 未创建')
        sys.exit(1)
