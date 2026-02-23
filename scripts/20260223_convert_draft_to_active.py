# -*- coding: utf-8 -*-
"""
将所有 draft 状态的项目转为 active 状态
项目状态简化为只有 active（进行中）和 completed（已完成）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader

app = create_app()

with app.app_context():
    draft_projects = ProjectHeader.query.filter_by(status='draft').all()
    count = len(draft_projects)

    if count == 0:
        print("没有 draft 状态的项目，无需转换")
    else:
        print(f"找到 {count} 个 draft 状态的项目，正在转换为 active...")
        for p in draft_projects:
            print(f"  {p.hid}: draft -> active")
            p.status = 'active'

        db.session.commit()
        print(f"已成功将 {count} 个项目从 draft 转换为 active")
