# 插件管理

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()


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

    # 初始化Flask-Mail
    mail.init_app(app)

    # 初始化Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.staff_login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    # 用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        from .auth.models import AuthUser
        return AuthUser.query.get(int(user_id))
    
    # 未授权处理器
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, redirect, url_for, flash
        flash('请先登录', 'warning')
        return redirect(url_for('auth_profile.staff_login', next=request.url))

    # 导入模型并创建所有表（如果未跳过）
    if not app.config.get('SKIP_DB_INIT', False):
        with app.app_context():
            try:
                db.create_all()
                print("✅ 数据库表创建完成")
            except Exception as e:
                print(f"⚠️ 数据库连接失败: {e}")
                print("💡 提示：请检查数据库连接配置或IP白名单设置")
    else:
        print("⏭️ 跳过数据库初始化")

# 在需要使用模型时在各自的模块中导入

