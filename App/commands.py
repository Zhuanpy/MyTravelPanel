from flask.cli import AppGroup
from scripts.update_visalinks import update_visalinks

def init_app(app):
    # 创建命令组
    db_cli = AppGroup('db')
    
    # 注册命令
    db_cli.add_command(update_visalinks)
    
    # 将命令组添加到应用
    app.cli.add_command(db_cli) 