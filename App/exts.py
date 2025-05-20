# 插件管理

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()


def init_exts(app):
    # 初始化数据库
    db.init_app(app=app)
    migrate.init_app(app=app, db=db)

    # 初始化缓存
    cache_config = {
        'CACHE_TYPE': 'simple',  # 使用简单的内存缓存，生产环境可以改用 redis
        'CACHE_DEFAULT_TIMEOUT': 3600  # 默认缓存时间1小时
    }
    app.config.from_mapping(cache_config)
    cache.init_app(app)

    # 导入模型并创建所有表
    with app.app_context():
        from . import models  # 这里只导入模块，具体模型在需要时导入
        db.create_all()
    # # 仅在需要时初始化数据库
    # if app.config.get('INIT_DB', False):
    #     with app.app_context():
    #         db.create_all()

# 在需要使用模型时在各自的模块中导入

