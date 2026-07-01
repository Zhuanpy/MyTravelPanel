# -*- coding: utf-8 -*-
"""
给客户公司写入 alias（简称），让公司搜索 API 能命中纯缩写

背景：/company/api/search 现在按分词匹配 company_name + company_code + alias。
      KATONG、SINOCON 等缩写是公司名子串，靠 name 已能搜到；
      但 QJEC、CHB 这类纯缩写既不在公司名里、company_code 又存着真实 UEN，
      不能覆盖 UEN，所以用独立的 alias 字段承载缩写。

依赖迁移：先跑 scripts/20260701_add_company_alias.py 加列。

安全策略：
    - alias -> 公司ID 映射经人工核对（本会话中已逐条查证 name/UEN）。
    - 只收录"name 搜不到、需要 alias"的缩写；name 已能搜到的不必写。
    - 不触碰 company_code（UEN）。
    - alias 已有且不同则默认跳过（--force 覆盖）；dry-run 默认，--commit 才写库。

运行：
    python scripts/20260701_set_company_aliases.py            # 预览
    python scripts/20260701_set_company_aliases.py --commit   # 写库
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.projects.models.project import CustomerCompany

# alias -> (company_id, 期望公司名关键词用于核对)
# 仅收录 name 搜不到、确需 alias 的纯缩写。已核对：
#   QJEC = QINGJIAN ENGINEERING & CONSTRUCTION (id 75, code=UEN 201003765E)
#   CHB  = CHINA HARBOUR (SINGAPORE) ENGINEERING (id 3, code=CH(0703)
# 注：KATONG 应为 id=66(name可搜到，无需alias)；EASYBUILD 库中查无此公司，均未收录。
ALIAS_MAP = {
    'QJEC': (75, 'QINGJIAN ENGINEERING'),
    'CHB': (3, 'CHINA HARBOUR'),
}


def main():
    # --commit 手动写库；--execute 为 server_update.sh 部署时传入，同样执行写入。
    commit = '--commit' in sys.argv or '--execute' in sys.argv
    force = '--force' in sys.argv

    app = create_app()
    with app.app_context():
        to_write, skipped, missing, mismatch = [], [], [], []

        for alias, (cid, expect_kw) in ALIAS_MAP.items():
            company = db.session.get(CustomerCompany, cid)
            if company is None:
                missing.append((alias, cid))
                continue

            # 核对：公司名应含期望关键词，防止映射写错对象
            if expect_kw and expect_kw.upper() not in (company.company_name or '').upper():
                mismatch.append((alias, cid, company.company_name, expect_kw))
                continue

            existing = (company.alias or '').strip()
            if existing and existing != alias and not force:
                skipped.append((alias, company.company_name, existing))
                continue

            to_write.append((alias, company, existing))

        print("=" * 70)
        print("将写入 alias（不触碰 company_code / UEN）:")
        for alias, company, existing in to_write:
            note = f'（覆盖旧 alias {existing!r}）' if existing else ''
            print(f"  [{alias:8}] id={company.id:<5} {company.company_name}  code={company.company_code!r} {note}")
        if not to_write:
            print("  （无）")

        if skipped:
            print("-" * 70)
            print("跳过（alias 已有其它值，--force 覆盖）:")
            for alias, name, existing in skipped:
                print(f"  [{alias:8}] {name}  现有 alias={existing!r}")
        if mismatch:
            print("-" * 70)
            print("⚠️ 跳过（公司名与期望不符，映射可能有误，请人工核对）:")
            for alias, cid, name, kw in mismatch:
                print(f"  [{alias:8}] id={cid} 实际='{name}' 期望含'{kw}'")
        if missing:
            print("-" * 70)
            print("⚠️ 找不到公司ID:")
            for alias, cid in missing:
                print(f"  [{alias:8}] id={cid}")

        print("=" * 70)
        if not commit:
            print(f"DRY-RUN：预览 {len(to_write)} 条改动，未写库。加 --commit 执行。")
            return

        for alias, company, _existing in to_write:
            company.alias = alias
        db.session.commit()
        print(f"✅ 已写入 {len(to_write)} 条 alias。")


if __name__ == '__main__':
    main()
