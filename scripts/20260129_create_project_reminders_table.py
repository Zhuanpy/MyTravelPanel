# -*- coding: utf-8 -*-
"""
创建项目提醒表 project_reminders
支持一个项目关联多条提醒
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 检查表是否已存在
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    if 'project_reminders' in existing_tables:
        print("表 project_reminders 已存在，跳过创建")
    else:
        # 创建表
        sql = """
        CREATE TABLE project_reminders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            header_id INT NOT NULL COMMENT '项目ID',
            reminder_event VARCHAR(200) NOT NULL COMMENT '提醒事件描述',
            reminder_date DATE NOT NULL COMMENT '提醒日期',
            is_completed TINYINT(1) DEFAULT 0 COMMENT '是否已完成',
            reminder_sent TINYINT(1) DEFAULT 0 COMMENT '是否已发送提醒',
            created_by VARCHAR(100) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            FOREIGN KEY (header_id) REFERENCES project_headers(id) ON DELETE CASCADE,
            INDEX idx_header_id (header_id),
            INDEX idx_reminder_date (reminder_date),
            INDEX idx_is_completed (is_completed)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目提醒表';
        """
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
            print("成功创建表 project_reminders")
        except Exception as e:
            db.session.rollback()
            print(f"创建表失败: {e}")
