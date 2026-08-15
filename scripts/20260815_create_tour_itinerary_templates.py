# -*- coding: utf-8 -*-
"""
迁移脚本：创建行程模板库表 tour_itinerary_templates

用途：把某个团组排好的每日行程存成模板，下次类似线路直接调用。
模板正文（payload）就是 tour_projects._group_to_template() 的产物，
每天记的是 day_offset（相对出发日偏移），所以能自动平移到任何出发日期。

权限：全员共享可调用；仅创建人与管理员可改名/覆盖/删除。

幂等：表已存在则跳过。
运行方式: python scripts/20260815_create_tour_itinerary_templates.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from sqlalchemy import text
from App_new import create_app
from App_new.exts import db
from App_new.business.tour.models.ItineraryTemplate import TourItineraryTemplate

app = create_app()

TABLE = 'tour_itinerary_templates'

with app.app_context():
    exists = db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t
        """
    ), {'t': TABLE}).scalar()

    if exists:
        print(f"表 {TABLE} 已存在，无需创建。")
    else:
        try:
            # 用模型定义建表，避免 DDL 与模型漂移
            TourItineraryTemplate.__table__.create(db.engine)
            print(f"成功创建表 {TABLE}")
        except Exception as e:
            print(f"建表失败：{e}")
            raise

    # 索引：列表页按名称/目的地搜索，按最近使用排序
    for index_name, columns in (
        ('idx_tpl_destination', 'destination'),
        ('idx_tpl_last_used', 'last_used_at'),
    ):
        has_index = db.session.execute(text(
            """
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i
            """
        ), {'t': TABLE, 'i': index_name}).scalar()

        if has_index:
            print(f"  索引 {index_name} 已存在，跳过。")
            continue
        try:
            db.session.execute(text(f"CREATE INDEX {index_name} ON {TABLE} ({columns})"))
            db.session.commit()
            print(f"  创建索引 {index_name} ({columns})")
        except Exception as e:
            db.session.rollback()
            # 索引建不上不影响功能，打日志继续
            print(f"  创建索引 {index_name} 失败（不影响功能）：{e}")

    print("完成。页面入口：项目编辑页 → 每日行程安排 → 「行程模板」下拉菜单。")
