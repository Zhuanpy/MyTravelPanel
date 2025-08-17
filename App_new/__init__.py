# -*- coding: utf-8 -*-
"""
新架构的Flask应用工厂
按模块化设计重构后的应用入口
"""

from flask import Flask, send_from_directory
import os
from flask_migrate import Migrate
from datetime import timedelta
import logging
import json

# 导入扩展和配置
from App.exts import db, init_exts
from App.utils.cache import cache
from App.config import Config
from App.utils.background_tasks import TodoReminder
from App.utils.exceptions import register_error_handlers

# 导入认证模块
from .auth.routes import auth_bp
from .auth.decorators import login_required

# 导入业务模块蓝图
from .business.visa.routes import visa_bp
from .business.flight.routes import flight_bp
from .business.tour.routes import tour_bp
from .business.finance.routes_account import account_bp
from .business.finance.routes_statement import statement_bp
from .business.finance.routes_supplier import supplier_bp

# 导入共享模块
from .shared.views import dex
from .shared.routes_utils import utils_bp
from .shared.routes_files import files_bp

migrate = Migrate()

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 验证配置
    Config.validate_config()

    # 配置日志
    configure_logging(app)

    # 初始化插件
    init_exts(app=app)
    migrate.init_app(app, db)
    
    # 确保CSRF保护正确初始化
    from App.exts import csrf
    csrf.init_app(app)

    # 注册错误处理器
    register_error_handlers(app)

    # 推荐使用环境变量来设置 SECRET_KEY，确保安全性
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 配置缓存
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    cache.init_app(app)

    # 注册蓝图 - 新架构
    register_blueprints(app)

    # 配置静态文件处理
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    # 兼容浏览器直接请求 /favicon.ico
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            app.static_folder,
            'favicon.ico',
            mimetype='image/x-icon'
        )

    # 初始化提醒服务
    app.reminder = TodoReminder(app)
    with app.app_context():
        app.reminder.start()

    # 添加模板过滤器
    register_template_filters(app)

    return app


def register_blueprints(app):
    """注册所有蓝图"""
    
    # 核心模块
    app.register_blueprint(dex)  # 主页面
    
    # 认证模块
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # 业务模块
    app.register_blueprint(visa_bp, url_prefix='/business/visa')
    app.register_blueprint(flight_bp, url_prefix='/business/flight')
    app.register_blueprint(tour_bp, url_prefix='/business/tour')
    
    # 财务模块
    app.register_blueprint(account_bp, url_prefix='/business/finance/account')
    app.register_blueprint(statement_bp, url_prefix='/business/finance/statement')
    app.register_blueprint(supplier_bp, url_prefix='/business/finance/supplier')
    
    # 共享模块
    app.register_blueprint(utils_bp, url_prefix='/shared/utils')
    app.register_blueprint(files_bp, url_prefix='/shared/files')


def register_template_filters(app):
    """注册模板过滤器"""
    @app.template_filter('from_json')
    def from_json_filter(value):
        """将JSON字符串转换为Python对象"""
        if value is None:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @app.template_filter('dict_except')
    def dict_except_filter(dictionary, key_to_exclude):
        """从字典中排除指定键的过滤器"""
        if dictionary is None:
            return {}
        result = dict(dictionary)
        result.pop(key_to_exclude, None)
        return result


def configure_logging(app):
    """配置日志系统"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = logging.FileHandler('logs/travelpanel.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('TravelPanel startup - New Architecture')
    else:
        app.logger.setLevel(logging.DEBUG)
