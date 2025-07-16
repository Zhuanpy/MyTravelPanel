from flask import Flask, send_from_directory
import os
from flask_migrate import Migrate

from .routes.views import dex
from .exts import db, init_exts
from .utils.cache import cache
from datetime import timedelta
from .config import Config
from App.utils.background_tasks import TodoReminder
from .utils.exceptions import register_error_handlers
import logging
import json

from App.routes.Utils.statement import statement_blue
from App.routes.Utils.utils_tasks import utils_blue

# 导入所有模型
from .models.User import User
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, ProjectEO
from App.models.Product.BusinessType import BusinessType
from App.models.Product.Suppliers import Supplier

# 导入签证相关的路由
from App.routes.projects.VisaProjects.visa_basic_info import visa_basic
from App.routes.projects.VisaProjects.visa_home import visa_home
from App.routes.projects.VisaProjects.visa_documents import visa_documents
from App.routes.projects.VisaProjects.visa_documents_list import visa_documents_list
from App.routes.projects.VisaProjects.visa_links import visa_links
from App.routes.projects.VisaProjects.visa_files import visa_files
from App.routes.projects.VisaProjects.visa_project import visa_project

# 导入 项目相关的路由
from App.routes.projects.BookingProject.project import projects
from .routes.business_type import business_types

# 导入客户公司管理路由
from App.routes.company import company

# 导入机票相关的路由
from App.routes.projects.FlightProjects.flights_home_routes import flight_home
from App.routes.projects.FlightProjects.flights_schedule import flights_schedule
from App.routes.projects.FlightProjects.flights_booking_routes import flights_booking
from App.routes.projects.FlightProjects.flights_athina_routes import flights_athina

# 导入所有utils相关路由
from App.routes.Utils.utils_company_info import company_info
from App.routes.Utils.account import account_routes
from App.routes.Utils.utils import utils_process

# 导入 配套相关的路由
from .routes.tour_package import package_blue
from .routes.supplier import supplier
from .routes.tour_product_details import product_details
from .routes.package_budget import package_budget

# 导入旅游项目相关的路由
from .routes.projects.TourProjects.tour_projects import tour_projects

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 验证配置
    Config.validate_config()

    # 配置日志
    configure_logging(app)

    # 初始化插件
    init_exts(app=app)
    migrate.init_app(app, db)

    # 注册错误处理器
    register_error_handlers(app)

    app.register_blueprint(dex)

    # 推荐使用环境变量来设置 SECRET_KEY，确保安全性
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key')  # 替换为实际的密钥

    # 配置缓存
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    # 初始化缓存
    cache.init_app(app)

    # 暂时禁用 Flask-Login，避免认证重定向问题
    # login_manager = LoginManager()
    # login_manager.init_app(app)
    # login_manager.login_view = 'dex.index'  # 设置登录视图为首页，避免302重定向

    # @login_manager.user_loader
    # def load_user(user_id):
    #     # todo 完成 User 相关内容
    #     return User.query.get(int(user_id))
    
    # # 临时禁用认证要求，避免302重定向问题
    # @login_manager.unauthorized_handler
    # def unauthorized():
    #     # 对于未认证的用户，直接重定向到首页而不是登录页面
    #     return redirect(url_for('dex.index'))

    # 注册蓝图
    app.register_blueprint(utils_blue, url_prefix='/utils')
    app.register_blueprint(utils_process, url_prefix='/utils_process')

    # 注册 visa 相关的蓝图
    app.register_blueprint(visa_home, url_prefix='/visa/home')
    app.register_blueprint(visa_basic, url_prefix='/visa/basic')
    app.register_blueprint(visa_documents, url_prefix='/visa/documents')
    app.register_blueprint(visa_documents_list, url_prefix='/visa/documents_list')
    app.register_blueprint(visa_links, url_prefix='/visa/links')
    app.register_blueprint(visa_files, url_prefix='/visa/files')
    app.register_blueprint(visa_project, url_prefix='/visa/project')

    app.register_blueprint(projects, url_prefix='/projects')
    app.register_blueprint(business_types, url_prefix='/business_types')
    
    # 注册客户公司管理蓝图
    app.register_blueprint(company, url_prefix='/customer_companies')

    app.register_blueprint(flight_home, url_prefix='/flight_home')
    app.register_blueprint(flights_schedule, url_prefix='/flight_schedule')
    app.register_blueprint(flights_booking, url_prefix='/flights_booking')
    app.register_blueprint(flights_athina, url_prefix='/flights_athina')

    app.register_blueprint(company_info, url_prefix='/company')
    app.register_blueprint(account_routes, url_prefix='/account')
    app.register_blueprint(package_blue, url_prefix='/package')
    app.register_blueprint(supplier, url_prefix='/supplier')
    app.register_blueprint(product_details, url_prefix='/product_details')
    app.register_blueprint(package_budget, url_prefix='/package_budget')

    # 注册旅游项目相关的蓝图
    app.register_blueprint(tour_projects, url_prefix='/tour_projects')

    app.register_blueprint(statement_blue, url_prefix='/statement')

    # app.register_blueprint(visa_bp, url_prefix='/visa')

    # 配置静态文件处理
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    # 添加对 .well-known 目录的支持
    @app.route('/.well-known/appspecific/<path:filename>')
    def well_known(filename):
        return send_from_directory(
            os.path.join(app.static_folder, '.well-known', 'appspecific'),
            filename
        )

    @app.cli.command("reset-db")
    def reset_db():
        """Reset the database."""
        with app.app_context():
            # Drop all tables
            db.drop_all()
            # Create all tables
            db.create_all()
            print("Database has been reset.")

    # 初始化提醒服务
    app.reminder = TodoReminder(app)
    
    # 使用应用上下文初始化提醒服务
    with app.app_context():
        app.reminder.start()

    # 添加模板过滤器
    @app.template_filter('from_json')
    def from_json_filter(value):
        """将JSON字符串转换为Python对象"""
        if value is None:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}

    return app


def configure_logging(app):
    """配置日志系统"""
    if not app.debug and not app.testing:
        # 生产环境日志配置
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = logging.FileHandler('logs/travelpanel.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('TravelPanel startup')
    else:
        # 开发环境日志配置
        app.logger.setLevel(logging.DEBUG)
