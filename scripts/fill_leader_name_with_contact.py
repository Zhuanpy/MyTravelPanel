#!/usr/bin/env python3
"""
将 project_headers 表中 leader_name 为空的记录，用 contact 字段补充
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.projects.BookingProject import ProjectHeader

def fill_leader_name_with_contact():
    app = create_app()
    with app.app_context():
        # 查询 leader_name 为空且 contact 不为空的记录
        headers = ProjectHeader.query.filter(
            (ProjectHeader.leader_name == None) | (ProjectHeader.leader_name == ''),
            ProjectHeader.contact != None,
            ProjectHeader.contact != ''
        ).all()
        print(f"共找到 {len(headers)} 条需要补充的记录")
        for header in headers:
            print(f"HID: {header.hid}, 原负责人: {header.leader_name}, 联系人: {header.contact}")
            header.leader_name = header.contact
        db.session.commit()
        print("已全部补充完成！")

if __name__ == "__main__":
    fill_leader_name_with_contact() 