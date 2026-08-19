# -*- coding: utf-8 -*-
"""
迁移脚本：行程模板库增加 country / city 字段

背景：原来只有一个自由填写的 destination，各人写法不一（日本 / Japan / 东京），
筛选筛不准。改为按 travel_products_city（ProductCity）的国家城市口径存两个字段，
和配套产品用同一套词；destination 保留作线路标签（如"北海道深度游"）。

顺带把已有数据里能对上的 destination 回填到 country / city：
  - destination 完全等于某个 city_name  → 填 city + 该城市对应的 country_name
  - destination 完全等于某个 country_name → 填 country
对不上的保持为空，由业务在页面上补。

幂等：字段/索引已存在则跳过；回填只动 country 和 city 都为空的行。
运行方式: python scripts/20260819_add_itinerary_template_country_city.py
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

app = create_app()

TABLE = 'tour_itinerary_templates'

COLUMNS = (
    ('country', "VARCHAR(100) NULL COMMENT '国家（对齐 travel_products_city.country_name）'"),
    ('city', "VARCHAR(100) NULL COMMENT '城市（对齐 travel_products_city.city_name）'"),
)

INDEXES = (
    ('idx_tpl_country', 'country'),
    ('idx_tpl_city', 'city'),
)


def column_exists(column):
    return db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
        """
    ), {'t': TABLE, 'c': column}).scalar()


def index_exists(index_name):
    return db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i
        """
    ), {'t': TABLE, 'i': index_name}).scalar()


with app.app_context():
    table_exists = db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t
        """
    ), {'t': TABLE}).scalar()

    if not table_exists:
        print(f"表 {TABLE} 不存在，请先运行 20260815_create_tour_itinerary_templates.py")
        sys.exit(1)

    # 1) 加字段
    for column, ddl in COLUMNS:
        if column_exists(column):
            print(f"字段 {column} 已存在，跳过。")
            continue
        try:
            db.session.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {column} {ddl}"))
            db.session.commit()
            print(f"新增字段 {column}")
        except Exception as e:
            db.session.rollback()
            print(f"新增字段 {column} 失败：{e}")
            raise

    # 2) 加索引（筛选走这两列）
    for index_name, column in INDEXES:
        if index_exists(index_name):
            print(f"  索引 {index_name} 已存在，跳过。")
            continue
        try:
            db.session.execute(text(f"CREATE INDEX {index_name} ON {TABLE} ({column})"))
            db.session.commit()
            print(f"  创建索引 {index_name} ({column})")
        except Exception as e:
            db.session.rollback()
            # 索引建不上不影响功能
            print(f"  创建索引 {index_name} 失败（不影响功能）：{e}")

    # 3) 回填：只处理 country/city 都还空着的行，不覆盖任何已填的值
    has_city_table = db.session.execute(text(
        """
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'travel_products_city'
        """
    )).scalar()

    if not has_city_table:
        print("未找到 travel_products_city，跳过回填。")
    else:
        try:
            by_city = db.session.execute(text(
                f"""
                UPDATE {TABLE} t
                JOIN (
                    SELECT city_name, MIN(country_name) AS country_name
                    FROM travel_products_city
                    WHERE city_name IS NOT NULL AND city_name <> ''
                    GROUP BY city_name
                ) c ON TRIM(t.destination) = c.city_name
                SET t.city = c.city_name, t.country = c.country_name
                WHERE t.country IS NULL AND t.city IS NULL
                  AND t.destination IS NOT NULL AND t.destination <> ''
                """
            )).rowcount

            by_country = db.session.execute(text(
                f"""
                UPDATE {TABLE} t
                JOIN (
                    SELECT DISTINCT country_name
                    FROM travel_products_city
                    WHERE country_name IS NOT NULL AND country_name <> ''
                ) c ON TRIM(t.destination) = c.country_name
                SET t.country = c.country_name
                WHERE t.country IS NULL AND t.city IS NULL
                  AND t.destination IS NOT NULL AND t.destination <> ''
                """
            )).rowcount

            db.session.commit()
            print(f"回填完成：按城市匹配 {by_city} 条，按国家匹配 {by_country} 条。")
        except Exception as e:
            db.session.rollback()
            print(f"回填失败（字段已加好，可在页面上手工补）：{e}")

        remaining = db.session.execute(text(
            f"SELECT COUNT(*) FROM {TABLE} WHERE country IS NULL"
        )).scalar()
        if remaining:
            print(f"还有 {remaining} 条模板没有国家，到「行程模板库」页面逐条编辑补上即可。")

    print("完成。页面入口：配套预算 → 旅游项目 → 行程模板库。")
