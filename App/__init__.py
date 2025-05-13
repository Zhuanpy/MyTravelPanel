from flask import Flask
import os
from flask_migrate import Migrate
from flask_login import LoginManager
from .routes.views import dex
from .exts import init_exts, db
from .utils.cache import cache
from datetime import timedelta
from .routes.files_tasks import utils_blue
from .routes.visas import visa_routes

from .routes.flights_home_routes import flight_home
from .routes.flights_schedule_routes import flights_schedule
from .routes.flights_booking_routes import flights_booking
from .routes.flights_athina_routes import flights_athina

from .routes.files_company_info import company_info
from .routes.files_account import account_routes
from .routes.tour_package import package_blue
from .routes.supplier import supplier
from .routes.tour_product_details import product_details
from .routes.files import files_process
from .routes.statement import statement_blue

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
        # todo 完成 User 相关内容
        from App.models.User import User  # 避免循环导入
        return User.query.get(int(user_id))

    # 初始化数据库迁移
    migrate = Migrate(app, db)

    # 注册蓝图
    app.register_blueprint(utils_blue, url_prefix='/utils')
    app.register_blueprint(visa_routes, url_prefix='/visa')

    app.register_blueprint(flight_home, url_prefix='/flight_home')
    app.register_blueprint(flights_schedule, url_prefix='/flight_schedule')
    app.register_blueprint(flights_booking, url_prefix='/flight_booking')
    app.register_blueprint(flights_athina, url_prefix='/flights_athina')

    app.register_blueprint(company_info, url_prefix='/company')
    app.register_blueprint(account_routes, url_prefix='/account')
    app.register_blueprint(package_blue, url_prefix='/package')
    app.register_blueprint(supplier, url_prefix='/supplier')
    app.register_blueprint(product_details, url_prefix='/product_details')
    app.register_blueprint(files_process, url_prefix='/files')
    app.register_blueprint(statement_blue, url_prefix='/statement')

    # 配置静态文件处理
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    return app
