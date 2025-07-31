# 插件管理

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
login_manager = LoginManager()


def init_exts(app):
    # 初始化数据库
    db.init_app(app=app)
    migrate.init_app(app=app, db=db)

    # 初始化CSRF保护
    csrf.init_app(app)

    # 初始化缓存
    cache_config = {
        'CACHE_TYPE': 'simple',  # 使用简单的内存缓存，生产环境可以改用 redis
        'CACHE_DEFAULT_TIMEOUT': 3600  # 默认缓存时间1小时
    }
    app.config.from_mapping(cache_config)
    cache.init_app(app)

    # 初始化Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    # 用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        from App.models.auth import AuthUser
        return AuthUser.query.get(int(user_id))
    
    # 未授权处理器
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, redirect, url_for, flash
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    # 导入模型并创建所有表
    with app.app_context():
        db.create_all()

# 在需要使用模型时在各自的模块中导入

