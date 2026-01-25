# -*- coding: utf-8 -*-
"""
EO表添加 is_paid 字段，分离业务状态和付款状态

修改内容：
1. 添加 is_paid 布尔字段
2. 将 status='paid' 的记录转换为 status='confirmed' + is_paid=True
3. 更新 status 枚举类型（移除 'paid', 'draft', 'cancelled'）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    try:
        # 步骤1：添加 is_paid 字段（先检查是否存在）
        print("步骤1：添加 is_paid 字段...")
        result = db.session.execute(db.text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'project_eos'
            AND column_name = 'is_paid'
        """))
        column_exists = result.scalar() > 0

        if not column_exists:
            db.session.execute(db.text("""
                ALTER TABLE project_eos
                ADD COLUMN is_paid TINYINT(1) NOT NULL DEFAULT 0
                COMMENT '是否已付款'
            """))
            db.session.commit()
            print("  - is_paid 字段添加成功")
        else:
            print("  - is_paid 字段已存在，跳过")

        # 步骤2：将 status='paid' 的记录转换
        print("\n步骤2：转换 status='paid' 的记录...")
        result = db.session.execute(db.text("""
            UPDATE project_eos
            SET is_paid = 1, status = 'confirmed'
            WHERE status = 'paid'
        """))
        db.session.commit()
        print(f"  - 已转换 {result.rowcount} 条记录")

        # 步骤3：将 status='draft' 或 'cancelled' 的记录转换为 'confirmed'
        print("\n步骤3：转换 status='draft' 或 'cancelled' 的记录...")
        result = db.session.execute(db.text("""
            UPDATE project_eos
            SET status = 'confirmed'
            WHERE status IN ('draft', 'cancelled')
        """))
        db.session.commit()
        print(f"  - 已转换 {result.rowcount} 条记录")

        # 步骤4：更新 status 枚举类型
        print("\n步骤4：更新 status 枚举类型...")
        db.session.execute(db.text("""
            ALTER TABLE project_eos
            MODIFY COLUMN status ENUM('confirmed', 'void')
            NOT NULL DEFAULT 'confirmed'
            COMMENT '业务状态：confirmed已确认/void已作废'
        """))
        db.session.commit()
        print("  - status 枚举类型更新成功")

        # 验证结果
        print("\n验证结果...")
        result = db.session.execute(db.text("""
            SELECT status, is_paid, COUNT(*) as cnt
            FROM project_eos
            GROUP BY status, is_paid
        """))
        rows = result.fetchall()
        print("  状态分布：")
        for row in rows:
            status, is_paid, cnt = row
            paid_text = "已付款" if is_paid else "未付款"
            print(f"    - {status} / {paid_text}: {cnt} 条")

        print("\n迁移完成！")

    except Exception as e:
        db.session.rollback()
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
