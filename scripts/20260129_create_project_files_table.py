"""
创建项目文件表 project_files
用于存储项目相关的附件文件信息
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

    if 'project_files' in existing_tables:
        print("表 project_files 已存在，跳过创建")
    else:
        # 创建表
        sql = """
        CREATE TABLE project_files (
            id INT AUTO_INCREMENT PRIMARY KEY,
            header_id INT NOT NULL COMMENT '项目ID',
            filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
            stored_filename VARCHAR(255) NOT NULL COMMENT '存储文件名',
            file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
            file_size INT COMMENT '文件大小（字节）',
            file_type VARCHAR(100) COMMENT '文件类型/MIME类型',
            description VARCHAR(500) COMMENT '文件描述',
            uploaded_by VARCHAR(100) COMMENT '上传人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
            FOREIGN KEY (header_id) REFERENCES project_headers(id) ON DELETE CASCADE,
            INDEX idx_header_id (header_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目文件表';
        """
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
            print("成功创建表 project_files")
        except Exception as e:
            db.session.rollback()
            print(f"创建表失败: {e}")
