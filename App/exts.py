# 插件管理

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def init_exts(app):


    db.init_app(app=app)
    migrate.init_app(app=app, db=db)

    # 导入模型并创建所有表
    with app.app_context():
        from . import models  # 这里只导入模块，具体模型在需要时导入
        db.create_all()
    # # 仅在需要时初始化数据库
    # if app.config.get('INIT_DB', False):
    #     with app.app_context():
    #         db.create_all()

# 在需要使用模型时在各自的模块中导入

