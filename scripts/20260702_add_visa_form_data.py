"""
创建签证项目填表数据表 visa_project_form_data。

- 存每个签证项目、每个坐标序列(seq)要填的值(detail)
- 替代过去手工编辑项目文件夹 FormSample.xls 的做法
- 幂等: 仅创建尚不存在的表(db.create_all 不会动已存在的表)

运行方式: python scripts/20260702_add_visa_form_data.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
# 导入模型以确保表被注册到 metadata
from App_new.business.visa.models import VisaProjectFormData  # noqa: F401

app = create_app()

with app.app_context():
    db.create_all()
    # 校验表是否已存在
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    if insp.has_table('visa_project_form_data'):
        print('OK: 表 visa_project_form_data 已就绪')
    else:
        print('失败: 表 visa_project_form_data 未创建')
        sys.exit(1)
