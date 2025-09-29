# -*- coding: utf-8 -*-
"""
新架构的Flask应用工厂
按模块化设计重构后的应用入口（冲突已合并）
"""

from flask import Flask, send_from_directory, redirect
from flask_migrate import Migrate
from datetime import timedelta
import os

# 导入扩展和配置（新架构）
from .exts import db, init_exts
from .config import Config

migrate = Migrate()


def create_app():
    """应用工厂函数"""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(Config)

    # 追加模板目录，兼容分模块模板
    from jinja2 import ChoiceLoader, FileSystemLoader
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dirs = [
        os.path.join(base_dir, 'templates'),
        os.path.join(base_dir, 'templates', 'shared'),
        os.path.join(base_dir, 'templates', 'staff'),
        os.path.join(base_dir, 'templates', 'admin'),
        os.path.join(base_dir, 'templates', 'auth'),
        os.path.join(base_dir, 'templates', 'member'),
        os.path.join(base_dir, 'templates', 'guest'),
        os.path.join(base_dir, 'templates', 'business'),
        os.path.join(base_dir, 'templates', 'finance'),
    ]
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(searchpath=template_dir) for template_dir in template_dirs
    ])

    # 初始化扩展
    init_exts(app)
    migrate.init_app(app, db)
    app.permanent_session_lifetime = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    # /favicon.ico 兼容
    @app.route('/favicon.ico')
    def favicon():
        # 兼容新旧命名：优先使用 logo.ico，其次 favico.ico，最后 favicon.ico
        preferred = 'logo.ico'
        fallback1 = 'favico.ico'
        fallback2 = 'favicon.ico'
        
        if os.path.exists(os.path.join(app.static_folder, preferred)):
            icon_file = preferred
        elif os.path.exists(os.path.join(app.static_folder, fallback1)):
            icon_file = fallback1
        else:
            icon_file = fallback2
            
        return send_from_directory(app.static_folder, icon_file, mimetype='image/x-icon')

    @app.route('/favico.ico')
    def favico():
        # 直接提供 favico.ico（若不存在则回退到 favicon.ico）
        preferred = 'favico.ico'
        fallback = 'favicon.ico'
        icon_file = preferred if os.path.exists(os.path.join(app.static_folder, preferred)) else fallback
        return send_from_directory(app.static_folder, icon_file, mimetype='image/x-icon')

    # 根路径重定向到 /public/
    @app.route('/')
    def root_redirect():
        return redirect('/public/', code=301)

    # 导入所有模型以确保数据库表创建（按需导入）
    import_all_models()

    # 注册蓝图
    # 共享与公开
    from .shared.routes.views import dex
    app.register_blueprint(dex)
    from .guest.routes import guest_bp
    app.register_blueprint(guest_bp, url_prefix='/public')

    # 认证模块
    from .auth.routes import auth_bp
    from .shared.routes.auth import auth_profile
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_profile)

    # 管理员/会员/员工模块
    from .admin.routes.admin import admin
    app.register_blueprint(admin)
    from .member.routes.member import member
    app.register_blueprint(member)
    from .staff.routes.staff import staff
    app.register_blueprint(staff)

    # 项目管理（新架构）
    from .business.projects import projects_bp
    app.register_blueprint(projects_bp)

    # 航班模块
    from .business.flight.routes.flight_routes import flight_routes
    from .business.flight.routes.flights_home_routes import flight_home
    from .business.flight.routes.flights_booking_routes import flights_booking
    from .business.flight.routes.flights_schedule import flights_schedule
    from .business.flight.routes.flights_athina_routes import flights_athina
    app.register_blueprint(flight_routes, url_prefix='/flight_routes')
    app.register_blueprint(flight_home, url_prefix='/flight_home')
    app.register_blueprint(flights_booking, url_prefix='/flights_booking')
    app.register_blueprint(flights_schedule, url_prefix='/flight_schedule')
    app.register_blueprint(flights_athina, url_prefix='/flights_athina')

    # 签证模块
    from .business.visa.routes.visa_home import visa_home
    from .business.visa.routes.visa_basic_info import visa_basic
    from .business.visa.routes.visa_documents import visa_documents
    from .business.visa.routes.visa_documents_list import visa_documents_list
    from .business.visa.routes.visa_links import visa_links
    from .business.visa.routes.visa_files import visa_files
    from .business.visa.routes.visa_project import visa_project
    app.register_blueprint(visa_home, url_prefix='/visa')
    app.register_blueprint(visa_basic, url_prefix='/visa/basic')
    app.register_blueprint(visa_documents, url_prefix='/visa/documents')
    app.register_blueprint(visa_documents_list, url_prefix='/visa/documents_list')
    app.register_blueprint(visa_links, url_prefix='/visa/links')
    app.register_blueprint(visa_files, url_prefix='/visa/files')
    app.register_blueprint(visa_project, url_prefix='/visa/project')

    # 旅游模块
    from .business.tour.routes.routes import tour_bp
    from .business.tour.routes.tour_projects import tour_projects
    from .business.tour.routes.package_budget import package_budget
    from .business.tour.routes.tour_package import package_blue
    from .business.tour.routes.tour_product_details import product_details
    app.register_blueprint(tour_bp, url_prefix='/tour')
    app.register_blueprint(tour_projects, url_prefix='/tour/projects')
    app.register_blueprint(package_budget, url_prefix='/package_budget')
    app.register_blueprint(package_blue, url_prefix='/package')
    app.register_blueprint(product_details, url_prefix='/tour/product_details')

    # 工具与共享
    from .shared.routes.tasks import utils_blue
    from .shared.routes.utils import utils_process
    from .shared.routes.account import account_routes
    from .shared.routes.company_info import company_info
    from .shared.routes.company import company
    from .shared.routes.business_type import business_types
    from .shared.routes.supplier import supplier
    app.register_blueprint(utils_blue, url_prefix='/utils')
    app.register_blueprint(utils_process, url_prefix='/utils_process')
    app.register_blueprint(account_routes, url_prefix='/account')
    app.register_blueprint(company_info, url_prefix='/company_info')
    app.register_blueprint(company, url_prefix='/company')
    app.register_blueprint(business_types, url_prefix='/business_types')
    app.register_blueprint(supplier, url_prefix='/supplier')

    # 财务模块
    from .finance.routes.statement import statement_blue
    app.register_blueprint(statement_blue, url_prefix='/statement')
    
    # Athina 模块
    from .finance.routes.athina_routes import athina_blue
    app.register_blueprint(athina_blue, url_prefix='/statement')
    
    # SOA 模块
    from .finance.routes.athina_routes_soa import soa_blue
    app.register_blueprint(soa_blue, url_prefix='/statement')
    
    # 关键词管理模块
    from .finance.routes.keyword_routes import keyword_blue
    app.register_blueprint(keyword_blue, url_prefix='/statement')

    # 统一设置响应编码
    @app.after_request
    def add_encoding_header(response):
        if response.mimetype == 'text/html':
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

    # 全站品牌文案统一替换：将 MyTravelPanel 动态替换为 Joyeful Escapes（仅作用于HTML响应）
    @app.after_request
    def replace_brand_name(response):
        try:
            if response.mimetype == 'text/html':
                html = response.get_data(as_text=True)
                if 'MyTravelPanel' in html:
                    response.set_data(html.replace('MyTravelPanel', 'Joyeful Escapes'))
        except Exception:
            # 安静失败，不阻断响应
            pass
        return response

    return app


def import_all_models():
    """导入所有模型以确保数据库表创建（按需）"""
    try:
        from .auth.models.auth import AuthUser, Role, UserProfile, InvitationCode
        from .business.projects.models.receipt import ProjectReceipt
        from .business.projects.models.project import CustomerCompany, Customer, ProjectHeader
        from .business.projects.models.ref import ProjectRef, RefOrderItem
        from .business.projects.models.eo import ProjectEO
        from .finance.models.statement import (
            BankStatement, BankTransaction, SupplierStatement, SupplierStatementItem
        )
        # 银行关键词模型
        from .finance.models.bank_keywords import BankStatementKeyword, BankKeywordCategory
        # Athina账单模型
        from .finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
        # 航班
        try:
            from .business.flight.models.flight import ProjectFlightPassenger, ProjectFlightSegment
            from .business.flight.models.models import AirportData, FlightSchedule, FlightOrder
        except Exception:
            pass
        # 旅游
        try:
            from .business.tour.models.TourProject import TourGroup, TourItinerary, TourProject
            from .business.tour.models.PackageBudget import BudgetHeader, BudgetItem
            from .business.tour.models.Packagemodels import Product, ProductCity, CompanyInfo
        except Exception:
            pass
        # 共享
        try:
            from .shared.models.business_types import BusinessType, BusinessTypeExtension, BusinessTypeRelation
            from .shared.models.Suppliers import Supplier
            from .shared.models.Utilsmodels import Todo, Task
        except Exception:
            pass
    except Exception:
        # 安静失败，不阻断应用启动
        pass
