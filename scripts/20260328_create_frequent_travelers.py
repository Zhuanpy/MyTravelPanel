# -*- coding: utf-8 -*-
"""
创建常用旅客表 frequent_travelers
运行方式: python scripts/20260328_create_frequent_travelers.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS frequent_travelers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(10) COMMENT '称谓: MR/MS/MISS/MASTER',
    name VARCHAR(100) NOT NULL COMMENT '姓名',
    name_en VARCHAR(100) COMMENT '英文姓名',
    gender VARCHAR(10) COMMENT '性别: male/female',
    date_of_birth DATE COMMENT '出生日期',
    nationality VARCHAR(50) COMMENT '国籍',
    phone VARCHAR(30) COMMENT '联系电话',
    email VARCHAR(100) COMMENT '邮箱',
    passport_number VARCHAR(50) COMMENT '护照号码',
    passport_issuing_country VARCHAR(50) COMMENT '护照签发国',
    passport_expiry_date DATE COMMENT '护照有效期',
    id_card_number VARCHAR(50) COMMENT '身份证号码',
    airline_memberships TEXT COMMENT '航空会员信息，JSON格式',
    company_id INT COMMENT '关联客户公司ID',
    remarks TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES customer_companies(id) ON DELETE SET NULL,
    INDEX idx_name (name),
    INDEX idx_passport (passport_number),
    INDEX idx_phone (phone),
    INDEX idx_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常用旅客表';
"""

with app.app_context():
    try:
        # 检查表是否已存在
        result = db.session.execute(db.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'frequent_travelers'"
        ))
        exists = result.scalar()

        if exists:
            print('表 frequent_travelers 已存在，跳过创建')
        else:
            db.session.execute(db.text(CREATE_SQL))
            db.session.commit()
            print('表 frequent_travelers 创建成功！')

    except Exception as e:
        db.session.rollback()
        print(f'执行失败: {e}')
        sys.exit(1)
