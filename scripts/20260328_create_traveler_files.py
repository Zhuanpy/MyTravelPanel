# -*- coding: utf-8 -*-
"""
创建常用旅客文件表 traveler_files
运行方式: python scripts/20260328_create_traveler_files.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS traveler_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    traveler_id INT NOT NULL COMMENT '旅客ID',
    file_category VARCHAR(30) COMMENT '文件分类: passport/ic/membership_card/visa/other',
    filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
    stored_filename VARCHAR(255) NOT NULL COMMENT '存储文件名(UUID)',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_size INT COMMENT '文件大小(字节)',
    file_type VARCHAR(100) COMMENT 'MIME类型',
    description VARCHAR(200) COMMENT '文件描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (traveler_id) REFERENCES frequent_travelers(id) ON DELETE CASCADE,
    INDEX idx_traveler (traveler_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常用旅客文件表';
"""

with app.app_context():
    try:
        result = db.session.execute(db.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'traveler_files'"
        ))
        exists = result.scalar()

        if exists:
            print('表 traveler_files 已存在，跳过创建')
        else:
            db.session.execute(db.text(CREATE_SQL))
            db.session.commit()
            print('表 traveler_files 创建成功！')

    except Exception as e:
        db.session.rollback()
        print(f'执行失败: {e}')
        sys.exit(1)
