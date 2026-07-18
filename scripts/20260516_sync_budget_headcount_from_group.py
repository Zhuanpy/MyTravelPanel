# -*- coding: utf-8 -*-
"""
回填：把预算单的成人/儿童按"关联项目团队"修正同步

背景：
    预算单创建时拷贝了一次团队人数，之后团队拆分大人/小孩，两边漂移
    （如预算 16 = 10/0，但项目 74 团队已是 8/2）。

规则（与用户确认一致）：
    - 只处理"项目团队已拆分"的（tour_group.adult_count 非 NULL）
    - 多团时取该项目 id 最小的已拆分团为准（绝大多数单团）
    - 预算 (adult,child) 与团队不一致才更新

用法:
    python scripts/20260516_sync_budget_headcount_from_group.py            # 预览
    python scripts/20260516_sync_budget_headcount_from_group.py --execute  # 执行
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_config():
    try:
        from App_new.config import Config
        m = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)',
                     Config.SQLALCHEMY_DATABASE_URI)
        if m:
            return {'host': m.group(3), 'port': int(m.group(4)), 'user': m.group(1),
                    'password': m.group(2), 'database': m.group(5), 'charset': 'utf8mb4'}
    except Exception as e:
        print(f"警告: 读配置失败: {e}")
    return {'host': 'localhost', 'port': 3306, 'user': 'root',
            'password': os.environ.get('DB_PASSWORD', ''), 'database': 'travelindustry', 'charset': 'utf8mb4'}


def get_connection():
    import pymysql
    return pymysql.connect(**get_db_config())


# 每个项目取 id 最小的"已拆分"团作为基准
SQL_DIFF = """
SELECT b.id AS budget_id, b.package_name, b.project_id,
       b.adult_count AS b_adult, b.child_count AS b_child,
       g.adult_count AS g_adult, COALESCE(g.child_count,0) AS g_child
FROM package_budget_header b
JOIN (
    SELECT t.project_id, t.adult_count, t.child_count
    FROM tour_group t
    JOIN (
        SELECT project_id, MIN(id) AS min_id
        FROM tour_group
        WHERE adult_count IS NOT NULL
        GROUP BY project_id
    ) m ON m.project_id = t.project_id AND m.min_id = t.id
) g ON g.project_id = b.project_id
WHERE b.project_id IS NOT NULL
  AND g.adult_count >= 1
  AND (b.adult_count <> g.adult_count OR b.child_count <> COALESCE(g.child_count,0))
ORDER BY b.id
"""


def run(execute=False):
    print("=" * 78)
    print("预算成人/儿童按项目团队回填")
    print(f"模式: {'执行' if execute else '预览'}")
    print("=" * 78)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(SQL_DIFF)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        if not rows:
            print("没有需要修正的预算单。")
            return 0

        print(f"需修正 {len(rows)} 张预算单")
        print("-" * 78)
        print(f"{'预算ID':<8}{'项目':<8}{'套餐名':<24}{'预算(改前)':<14}{'团队(改后)':<12}")
        print("-" * 78)
        for r in rows:
            name = (r['package_name'] or '')[:22]
            print(f"{r['budget_id']:<8}{r['project_id']:<8}{name:<24}"
                  f"{str(r['b_adult'])+'/'+str(r['b_child']):<14}"
                  f"{str(r['g_adult'])+'/'+str(r['g_child']):<12}")
        print("-" * 78)

        if not execute:
            print("预览完成。加 --execute 执行。")
            return len(rows)

        for r in rows:
            cur.execute(
                "UPDATE package_budget_header SET adult_count=%s, child_count=%s, "
                "updated_at=NOW() WHERE id=%s",
                (r['g_adult'], r['g_child'], r['budget_id']))
        conn.commit()
        print(f"已修正 {len(rows)} 张预算单。")
        return len(rows)
    except Exception as e:
        conn.rollback()
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    ex = '--execute' in sys.argv or '-e' in sys.argv
    sys.exit(0 if run(execute=ex) >= 0 else 1)
