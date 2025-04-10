from flask import Flask
import os
from flask_migrate import Migrate
from flask_login import LoginManager
from .routes.views import dex
from .exts import init_exts, db
from .utils.cache import cache
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta

def create_app():
    app = Flask(__name__)
    app.register_blueprint(dex)

    # 推荐使用环境变量来设置 SECRET_KEY，确保安全性
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key')  # 替换为实际的密钥

    # 配置数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:***REMOVED****@localhost/travelindustry'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 配置缓存
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    # 初始化缓存
    cache.init_app(app)

    # 初始化插件
    init_exts(app=app)

    # 初始化 Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # 设置登录视图的端点

    @login_manager.user_loader
    def load_user(user_id):
        from App.models.User import User  # 避免循环导入
        return User.query.get(int(user_id))

    # 初始化数据库迁移
    migrate = Migrate(app, db)

    # 注册蓝图
    from .routes.routes_visa import visa_routes
    from .routes.route_flight import flight_blue
    from .routes.routes_files import files_process
    from .routes.routes_statement import statement_blue
    from .routes.routes_package import package_blue
    from .routes.routes_utils import utils_blue
    from .routes.files_deepseek import deepseek_routes
    from .routes.routes_supplier import supplier
    from .routes.TourProductDetails import product_details
    from .routes.CompanyInfo import company_info
    from .routes.routes_visa import visa_routes
    from .routes.route_flight import flight_blue
    from .routes.routes_account import account_routes

    app.register_blueprint(visa_routes, url_prefix='/visa')
    app.register_blueprint(flight_blue, url_prefix='/flights')
    app.register_blueprint(statement_blue)
    app.register_blueprint(files_process)
    app.register_blueprint(package_blue)
    app.register_blueprint(utils_blue, url_prefix='/utils_blue')
    app.register_blueprint(deepseek_routes, url_prefix='/deepseek')
    app.register_blueprint(supplier, url_prefix='/supplier')
    app.register_blueprint(product_details, url_prefix='/product_details')
    app.register_blueprint(company_info, url_prefix='/company_info')
    app.register_blueprint(account_routes)  # 不需要url_prefix，因为路由已经包含了完整路径

    # 配置静态文件处理
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    return app
