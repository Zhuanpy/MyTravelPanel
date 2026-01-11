# -*- coding: utf-8 -*-
"""
创建供应商付款记录表 supplier_payments
并在 project_eos 表添加 payment_record_id 字段

执行方式: python scripts/20260111_create_supplier_payment_table.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()


def create_supplier_payments_table():
    """创建供应商付款记录表"""
    with app.app_context():
        print("=" * 60)
        print("创建供应商付款记录表")
        print("=" * 60)

        # 检查表是否存在
        result = db.session.execute(text("SHOW TABLES LIKE 'supplier_payments'"))
        if result.fetchone():
            # 检查是否是新结构（有 payment_no 字段）
            result = db.session.execute(text("SHOW COLUMNS FROM supplier_payments LIKE 'payment_no'"))
            if result.fetchone():
                print("表 supplier_payments 已是新结构，跳过创建")
                return
            else:
                # 旧表，检查是否有数据
                result = db.session.execute(text("SELECT COUNT(*) FROM supplier_payments"))
                count = result.fetchone()[0]
                if count > 0:
                    print(f"警告: 旧表 supplier_payments 有 {count} 条数据，请手动处理")
                    return
                else:
                    print("删除旧的空表 supplier_payments...")
                    db.session.execute(text("DROP TABLE supplier_payments"))
                    db.session.commit()

        # 创建新表
        create_sql = """
        CREATE TABLE supplier_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            payment_no VARCHAR(30) NOT NULL UNIQUE COMMENT '付款编号',
            supplier_id INT COMMENT '供应商ID',
            payment_date DATE NOT NULL COMMENT '付款日期',
            total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0 COMMENT '付款总金额',
            currency VARCHAR(3) NOT NULL DEFAULT 'SGD' COMMENT '货币',
            payment_source ENUM('bank', 'prepayment', 'mixed') NOT NULL DEFAULT 'bank' COMMENT '付款来源',
            payment_voucher_no VARCHAR(50) COMMENT '银行付款凭证号',
            bank_account_id INT COMMENT '付款银行账户',
            prepayment_amount DECIMAL(12, 2) DEFAULT 0 COMMENT '使用预付账款金额',
            eo_count INT DEFAULT 0 COMMENT '包含EO数量',
            status ENUM('draft', 'confirmed', 'cancelled') NOT NULL DEFAULT 'confirmed' COMMENT '状态',
            remarks TEXT COMMENT '备注',
            journal_entry_id INT COMMENT '日记账分录ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(50) COMMENT '创建人',
            FOREIGN KEY (supplier_id) REFERENCES customer_companies(id) ON DELETE SET NULL,
            FOREIGN KEY (bank_account_id) REFERENCES project_chart_of_accounts(id) ON DELETE SET NULL,
            FOREIGN KEY (journal_entry_id) REFERENCES project_journal_entries(id) ON DELETE SET NULL,
            INDEX idx_payment_no (payment_no),
            INDEX idx_supplier_id (supplier_id),
            INDEX idx_payment_date (payment_date),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商付款记录表'
        """
        db.session.execute(text(create_sql))
        db.session.commit()
        print("表 supplier_payments 创建成功")


def add_payment_record_id_to_eos():
    """在 project_eos 表添加 payment_record_id 字段"""
    with app.app_context():
        print("\n" + "=" * 60)
        print("在 project_eos 表添加 payment_record_id 字段")
        print("=" * 60)

        # 检查字段是否存在
        result = db.session.execute(text(
            "SHOW COLUMNS FROM project_eos LIKE 'payment_record_id'"
        ))
        if result.fetchone():
            print("字段 payment_record_id 已存在，跳过")
        else:
            # 先添加字段（不带外键）
            alter_sql = """
            ALTER TABLE project_eos
            ADD COLUMN payment_record_id INT COMMENT '付款记录ID' AFTER tax
            """
            db.session.execute(text(alter_sql))
            db.session.commit()
            print("字段 payment_record_id 添加成功")

            # 再添加外键约束
            try:
                fk_sql = """
                ALTER TABLE project_eos
                ADD CONSTRAINT fk_eo_payment_record
                FOREIGN KEY (payment_record_id) REFERENCES supplier_payments(id) ON DELETE SET NULL
                """
                db.session.execute(text(fk_sql))
                db.session.commit()
                print("外键约束添加成功")
            except Exception as e:
                print(f"外键约束添加失败（非致命）: {e}")


def verify():
    """验证创建结果"""
    with app.app_context():
        print("\n" + "=" * 60)
        print("验证结果")
        print("=" * 60)

        # 检查 supplier_payments 表结构
        result = db.session.execute(text("DESCRIBE supplier_payments"))
        rows = result.fetchall()
        print("\nsupplier_payments 表结构:")
        for r in rows:
            print(f"  {r[0]}: {r[1]}")

        # 检查 project_eos 的 payment_record_id 字段
        result = db.session.execute(text(
            "SHOW COLUMNS FROM project_eos LIKE 'payment_record_id'"
        ))
        row = result.fetchone()
        if row:
            print(f"\nproject_eos.payment_record_id: {row[1]}")
        else:
            print("\n警告: project_eos.payment_record_id 字段不存在!")


def main():
    print("=" * 60)
    print("供应商付款记录表创建脚本")
    print("=" * 60)

    try:
        create_supplier_payments_table()
        add_payment_record_id_to_eos()
        verify()
        print("\n" + "=" * 60)
        print("脚本执行完成")
        print("=" * 60)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
