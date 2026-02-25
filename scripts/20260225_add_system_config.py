"""
创建 system_config 表并插入默认付款配置
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    conn = db.engine.connect()

    # 创建表
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS system_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT,
            description VARCHAR(200) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_config_key (config_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    conn.commit()
    print('system_config 表已创建')

    # 插入默认付款配置
    defaults = [
        ('payment_bank_name', '', '收款银行名称'),
        ('payment_account_name', '', '收款账户名'),
        ('payment_account_number', '', '收款账号'),
        ('payment_qr_image', '', '付款二维码图片路径'),
        ('payment_note', '', '付款备注说明'),
    ]
    for key, value, desc in defaults:
        result = conn.execute(db.text(
            "SELECT id FROM system_config WHERE config_key = :key"
        ), {'key': key})
        if not result.fetchone():
            conn.execute(db.text(
                "INSERT INTO system_config (config_key, config_value, description) VALUES (:key, :val, :desc)"
            ), {'key': key, 'val': value, 'desc': desc})
            print(f'  插入配置: {key}')
        else:
            print(f'  已存在: {key}')
    conn.commit()
    conn.close()
    print('完成')
