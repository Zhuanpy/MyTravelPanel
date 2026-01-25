# -*- coding: utf-8 -*-
"""
添加股东借款/还款匹配类型到 bank_transaction_matches 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

def migrate():
    """修改 match_type 枚举，添加 loan_borrow 和 loan_repay"""
    with app.app_context():
        try:
            # MySQL 修改枚举类型
            sql = """
            ALTER TABLE bank_transaction_matches
            MODIFY COLUMN match_type ENUM('receipt', 'eo', 'payment', 'prepayment', 'loan_borrow', 'loan_repay')
            NOT NULL COMMENT '匹配类型：receipt=收款，eo=EO，payment=付款，prepayment=预付款，loan_borrow=股东借款，loan_repay=股东还款'
            """
            db.session.execute(db.text(sql))
            db.session.commit()
            print("成功: match_type 枚举已更新，添加了 loan_borrow 和 loan_repay")

        except Exception as e:
            db.session.rollback()
            print(f"错误: {str(e)}")
            raise

if __name__ == '__main__':
    migrate()
