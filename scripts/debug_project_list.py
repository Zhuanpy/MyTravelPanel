# -*- coding: utf-8 -*-
"""
调试项目列表排序问题
检查 H1082 为什么没有显示在正常列表中
"""
import sys
sys.path.insert(0, '/var/www/MyTravelPanel')

from app_new import app

app.app_context().push()

from App_new.business.projects.models.project import ProjectHeader
from App_new.exts import db

print("=" * 50)
print("测试1: 基础排序查询 (前15条)")
print("=" * 50)
results = ProjectHeader.query.order_by(
    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
).limit(15).all()

for p in results:
    print(f"ID: {p.id}, HID: {p.hid}, Staff: {p.staff_name}")

print("\n" + "=" * 50)
print("测试2: 检查 H1082 是否在查询结果中")
print("=" * 50)
h1082 = ProjectHeader.query.filter_by(hid='H1082').first()
if h1082:
    print(f"H1082 存在: ID={h1082.id}, Staff={h1082.staff_name}, Company={h1082.company_id}")
else:
    print("H1082 不存在!")

print("\n" + "=" * 50)
print("测试3: 模拟完整的 list_projects 查询")
print("=" * 50)
from flask_login import current_user

# 模拟基础查询
base_query = ProjectHeader.query.options(
    db.joinedload(ProjectHeader.company)
)

# 排序
base_query = base_query.order_by(
    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
)

# 获取前15条
projects = base_query.limit(15).all()
print("模拟查询结果:")
for p in projects:
    company_name = p.company.company_name if p.company else 'None'
    print(f"ID: {p.id}, HID: {p.hid}, Company: {company_name}")

print("\n" + "=" * 50)
print("测试4: 检查是否有重复 HID")
print("=" * 50)
from sqlalchemy import func
duplicates = db.session.query(
    ProjectHeader.hid,
    func.count(ProjectHeader.id).label('count')
).group_by(ProjectHeader.hid).having(func.count(ProjectHeader.id) > 1).all()

if duplicates:
    print("发现重复 HID:")
    for hid, count in duplicates:
        print(f"  {hid}: {count} 条记录")
else:
    print("没有重复 HID")

print("\n" + "=" * 50)
print("测试5: 直接 SQL 查询对比")
print("=" * 50)
sql = """
SELECT id, hid, staff_name
FROM project_headers
ORDER BY CAST(SUBSTRING(hid, 2) AS UNSIGNED) DESC
LIMIT 15
"""
result = db.session.execute(db.text(sql))
print("直接 SQL 结果:")
for row in result:
    print(f"ID: {row[0]}, HID: {row[1]}, Staff: {row[2]}")

print("\n调试完成!")
