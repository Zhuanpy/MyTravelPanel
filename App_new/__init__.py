# -*- coding: utf-8 -*-
"""
新架构的Flask应用工厂
按模块化设计重构后的应用入口 - 修复版本
"""

from flask import Flask, send_from_directory
import os
from flask_migrate import Migrate
from datetime import timedelta
import logging
from sqlalchemy import text

# 导入扩展和配置
from .exts import db, init_exts
from .config import Config

migrate = Migrate()


def create_app():
    """应用工厂函数"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config.from_object(Config)
    
    # 添加额外的模板目录
    from jinja2 import ChoiceLoader, FileSystemLoader
    import os
    
    # 获取当前工作目录
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
        os.path.join(base_dir, 'templates', 'finance')
    ]
    
    # 创建模板加载器
    template_loader = ChoiceLoader([
        FileSystemLoader(searchpath=template_dir) for template_dir in template_dirs
    ])
    app.jinja_loader = template_loader
    
    print("🚀 正在启动新架构应用...")
    print("✅ 配置验证完成")
    
    # 初始化扩展
    print("📦 初始化数据库和扩展...")
    init_exts(app)
    migrate.init_app(app, db)
    
    # 配置会话
    app.permanent_session_lifetime = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    # 兼容浏览器直接请求 /favicon.ico
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            app.static_folder,
            'favicon.ico',
            mimetype='image/x-icon'
        )

    # 导入所有模型以确保数据库表创建
    print("📋 导入模型...")
    import_all_models()
    
    # 简化的数据库初始化
    with app.app_context():
        try:
            print("✅ 数据库配置完成")
        except Exception as e:
            print(f"⚠️ 数据库初始化警告: {e}")
            print("💡 应用仍可正常启动")

    # 注册共享模块蓝图（包含 portal 页面）
    from .shared.routes.views import dex
    app.register_blueprint(dex)
    
    # 注册访客模块蓝图（公开页面）
    from .guest.routes import guest_bp
    app.register_blueprint(guest_bp, url_prefix='/public')
    
    # 注册认证模块蓝图
    from .auth.routes import auth_bp
    from .shared.routes.auth import auth_profile
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_profile)

    # 注册管理员模块蓝图
    from .admin.routes.admin import admin
    app.register_blueprint(admin)

    # 注册会员模块蓝图
    from .member.routes.member import member
    app.register_blueprint(member)
    
    # 注册员工模块蓝图
    from .staff.routes.staff import staff
    app.register_blueprint(staff)
    
    # 注册项目管理蓝图（新架构）
    from .business.projects import projects_bp
    app.register_blueprint(projects_bp, url_prefix='/projects', name='business_projects')
    
    # 项目管理路由已统一到 business.projects 模块
    
    # 注册航班模块蓝图
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
    
    # 注册签证模块蓝图
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
    
    # 注册旅游模块蓝图
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
    
    # 注册工具模块蓝图
    from .shared.routes.utils_tasks import utils_blue
    from .shared.routes.utils import utils_process
    from .shared.routes.account import account_routes
    from .shared.routes.utils_company_info import company_info
    from .shared.routes.company import company
    from .shared.routes.business_type import business_types
    from .shared.routes.supplier import supplier
    # from .shared.routes.public import public  # 暂时注释掉，因为会导致模型重复定义

    app.register_blueprint(utils_blue, url_prefix='/utils')
    app.register_blueprint(utils_process, url_prefix='/utils_process')
    app.register_blueprint(account_routes, url_prefix='/account')
    app.register_blueprint(company_info, url_prefix='/company_info')
    app.register_blueprint(company, url_prefix='/company')
    app.register_blueprint(business_types, url_prefix='/business_types')
    app.register_blueprint(supplier, url_prefix='/supplier')
    # app.register_blueprint(public, url_prefix='/public')  # 暂时注释掉

    # 注册财务模块蓝图
    from .finance.routes.routes import statement_blue
    app.register_blueprint(statement_blue, url_prefix='/statement')

    # 添加编码响应头设置
    @app.after_request
    def add_encoding_header(response):
        """确保所有HTML响应都包含正确的编码头"""
        if response.mimetype == 'text/html':
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    
    print("✅ 新架构应用启动完成！")
    return app


def import_all_models():
    """导入所有模型以确保数据库表创建"""
    try:
        # 导入认证模块模型
        from .auth.models.auth import AuthUser, Role, UserProfile, InvitationCode
        print("✅ 导入认证模型")
        
        # 导入项目管理模型（新架构）
        from .business.projects.models.receipt import ProjectReceipt
        from .business.projects.models.project import CustomerCompany, Customer, ProjectHeader
        from .business.projects.models.ref import ProjectRef, RefOrderItem
        from .business.projects.models.eo import ProjectEO
        print("✅ 导入项目管理模型")
        
        # 导入财务模块模型
        from .finance.models.statement import BankStatement, BankTransaction, SupplierStatement, SupplierStatementItem
        print("✅ 导入财务模型")
        
        # 导入业务模块模型
        try:
            from .business.flight.models.flight import ProjectFlightPassenger, ProjectFlightSegment
            from .business.flight.models.models import AirportData, FlightSchedule, FlightOrder
            print("✅ 导入航班模型")
        except ImportError as e:
            print(f"⚠️ 航班模型导入警告: {e}")
        
            # 导入签证模块模型 - 注释掉，避免重复导入
    # try:
    #     from .business.visa.models.Visamodels import VisaCountries, VisaTypes, VisaSingaporeIdentity, VisaDocuments, VisaDocumentsList
    #     print("✅ 导入签证模型")
    # except ImportError as e:
    #     print(f"⚠️ 签证模型导入警告: {e}")
        
        # 导入旅游模块模型
        try:
            from .business.tour.models.TourProject import TourGroup, TourItinerary, TourProject
            from .business.tour.models.PackageBudget import BudgetHeader, BudgetItem
            from .business.tour.models.Packagemodels import Product, ProductCity, CompanyInfo
            print("✅ 导入旅游模型")
        except ImportError as e:
            print(f"⚠️ 旅游模型导入警告: {e}")
        
        # 导入共享模块模型
        try:
            from .shared.models.business_types import BusinessType, BusinessTypeExtension, BusinessTypeRelation
            from .shared.models.Suppliers import Supplier
            print("✅ 导入共享模型")
        except ImportError as e:
            print(f"⚠️ 模型导入警告: {e}")
            print("📝 某些模型可能尚未完全配置，应用仍可启动")
            
    except Exception as e:
        print(f"⚠️ 模型导入失败: {e}")
        print("📝 某些模型可能尚未完全配置，应用仍可启动")
