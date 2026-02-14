# -*- coding: utf-8 -*-
"""
创建 contact_inquiries 表（客户在线咨询）
运行方式: python scripts/20260214_create_contact_inquiries.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # 检查表是否已存在
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'contact_inquiries'"
        ))
        exists = result.scalar()

        if exists:
            print("contact_inquiries 表已存在，跳过")
        else:
            db.session.execute(text("""
                CREATE TABLE contact_inquiries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL COMMENT '客户姓名',
                    phone VARCHAR(30) NOT NULL COMMENT '客户电话',
                    email VARCHAR(150) NOT NULL COMMENT '客户邮箱',
                    service_type VARCHAR(50) NULL COMMENT '服务类型: visa/tour/flight/hotel/other',
                    message TEXT NOT NULL COMMENT '咨询内容',
                    status VARCHAR(20) NOT NULL DEFAULT 'new' COMMENT '状态: new/read/replied/closed',
                    assigned_to INT NULL COMMENT '分配给的员工ID',
                    staff_notes TEXT NULL COMMENT '内部备注',
                    ip_address VARCHAR(50) NULL COMMENT '客户IP地址',
                    user_agent VARCHAR(500) NULL COMMENT '客户浏览器信息',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
                    read_at DATETIME NULL COMMENT '已读时间',
                    replied_at DATETIME NULL COMMENT '回复时间',
                    CONSTRAINT fk_inquiry_assigned_to FOREIGN KEY (assigned_to) REFERENCES auth_users(id) ON DELETE SET NULL,
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户在线咨询'
            """))
            db.session.commit()
            print("成功创建 contact_inquiries 表")

    except Exception as e:
        db.session.rollback()
        print(f"执行失败: {e}")
