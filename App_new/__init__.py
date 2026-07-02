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
        os.path.join(base_dir, 'templates', 'mobile'),
    ]
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(searchpath=template_dir) for template_dir in template_dirs
    ])

    # 初始化扩展
    init_exts(app)
    migrate.init_app(app, db)
    app.permanent_session_lifetime = timedelta(days=1)
    app.config['STATIC_FOLDER'] = 'static'

    # 性能监控（慢请求 + 慢 SQL 日志，写入 logs/slow_request.log 与 logs/slow_query.log）
    from .shared.monitoring import init_monitoring
    init_monitoring(app)

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
    from .shared.routes.public import public
    app.register_blueprint(public)
    from .guest.routes import guest_bp
    app.register_blueprint(guest_bp, url_prefix='/public')

    # 认证模块
    from .auth import init_auth
    from .shared.routes.auth import auth_profile
    init_auth(app)
    app.register_blueprint(auth_profile)

    # 管理员/会员/员工模块
    from .admin.routes.admin import admin
    app.register_blueprint(admin)
    from .member.routes.member import member
    from .member.routes.orders import orders_bp
    from .member.routes.cart import cart_bp
    app.register_blueprint(member)
    app.register_blueprint(orders_bp)
    app.register_blueprint(cart_bp)
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
    from .business.flight.routes.flights_usbangla_routes import flights_usbangla
    from .business.flight.routes.passport_routes import flights_passport
    app.register_blueprint(flight_routes, url_prefix='/flight_routes')
    app.register_blueprint(flight_home, url_prefix='/flight_home')
    app.register_blueprint(flights_booking, url_prefix='/flights_booking')
    app.register_blueprint(flights_schedule, url_prefix='/flight_schedule')
    app.register_blueprint(flights_athina, url_prefix='/flights_athina')
    app.register_blueprint(flights_usbangla, url_prefix='/flights_usbangla')
    app.register_blueprint(flights_passport)

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
    from .business.tour.routes.tour_products import tour_products_bp
    from .business.tour.routes.package_budget import package_budget
    from .business.tour.routes.tour_package import package_blue
    from .business.tour.routes.tour_product_details import product_details
    app.register_blueprint(tour_bp, url_prefix='/tour')
    app.register_blueprint(tour_projects, url_prefix='/tour/projects')
    app.register_blueprint(tour_products_bp)  # 已包含 url_prefix='/tour/products'
    app.register_blueprint(package_budget, url_prefix='/package_budget')
    app.register_blueprint(package_blue, url_prefix='/package')
    app.register_blueprint(product_details, url_prefix='/tour/product_details')

    # 统一产品管理模块
    from .business.products import products_bp
    app.register_blueprint(products_bp)  # 已包含 url_prefix='/staff/products'

    # 工具与共享
    from .shared.routes.tasks import utils_blue
    from .shared.routes.utils import utils_process
    from .shared.routes.account import account_routes
    from .shared.routes.own_company import own_company
    from .shared.routes.corporate import corporate
    from .shared.routes.business_type import business_types
    from .shared.routes.supplier import supplier
    from .utils.routes.checklist import checklist_bp
    from .shared.models.routes_files import files_process
    from .shared.routes.hermes_api import hermes_api

    app.register_blueprint(utils_blue, url_prefix='/utils')
    app.register_blueprint(utils_process, url_prefix='/utils_process')
    app.register_blueprint(files_process, url_prefix='/files')
    app.register_blueprint(account_routes, url_prefix='/account')
    app.register_blueprint(own_company, url_prefix='/own_company')
    app.register_blueprint(corporate, url_prefix='/company')
    app.register_blueprint(business_types, url_prefix='/business_types')
    app.register_blueprint(supplier, url_prefix='/supplier')
    app.register_blueprint(checklist_bp)  # 任务清单蓝图，已包含 url_prefix='/utils/checklists'
    app.register_blueprint(hermes_api)  # Hermes 自描述接口，已包含 url_prefix='/api/hermes'

    # 财务模块 - 银行对账单路由
    from .finance.routes.uob_routes import uob_blue
    from .finance.routes.ocbc_routes import ocbc_blue
    from .finance.routes.cmb_routes import cmb_blue
    from .finance.routes.statement_common import statement_common_blue
    app.register_blueprint(uob_blue, url_prefix='/statement')
    app.register_blueprint(ocbc_blue, url_prefix='/statement')
    app.register_blueprint(cmb_blue, url_prefix='/statement')
    app.register_blueprint(statement_common_blue, url_prefix='/statement')
    
    # Athina 模块
    from .finance.routes.athina_routes import athina_blue
    app.register_blueprint(athina_blue, url_prefix='/statement')
    
    # SOA 模块
    from .finance.routes.athina_routes_soa import soa_blue
    app.register_blueprint(soa_blue, url_prefix='/statement')
    
    # 关键词管理模块
    from .finance.routes.keyword_routes import keyword_blue
    app.register_blueprint(keyword_blue, url_prefix='/statement')

    # 总账与会计科目模块
    from .finance.routes.ledger_routes import ledger_blue
    app.register_blueprint(ledger_blue, url_prefix='/ledger')

    # 银行流水与收款对比模块
    from .finance.routes.reconciliation_routes import reconciliation_bp
    app.register_blueprint(reconciliation_bp)

    # 移动端模块
    from .mobile import mobile_bp
    app.register_blueprint(mobile_bp)

    # 注册自定义Jinja2过滤器
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        """将JSON字符串转换为Python对象"""
        import json
        try:
            if value and isinstance(value, str):
                return json.loads(value)
            return value if value else {}
        except Exception:
            return {}

    @app.template_filter('is_absolute_path')
    def is_absolute_path(path):
        """判断路径是否是绝对路径"""
        import os
        if not path:
            return False
        path_str = str(path).replace('\\', '/')
        # 检查是否是URL
        if path_str.startswith('http://') or path_str.startswith('https://'):
            return False
        # 检查是否是Windows绝对路径（如 C:/ 或 D:/）
        if len(path_str) >= 3 and path_str[1] == ':' and path_str[2] == '/':
            return True
        # 检查是否是Unix绝对路径（以 / 开头）
        if path_str.startswith('/'):
            return True
        return False
    
    @app.template_filter('image_url')
    def image_url_filter(path):
        """
        智能处理图片URL，根据路径格式返回正确的URL
        
        支持以下格式：
        1. 完整URL (http:// 或 https://) - 直接返回
        2. 相对路径 (uploads/xxx) - 转换为静态文件URL
        3. 绝对路径 - 提取文件名后转换
        """
        from flask import url_for
        import os
        
        if not path:
            return ''
        
        path_str = str(path).replace('\\', '/')
        
        # 如果已经是完整URL，直接返回
        if path_str.startswith('http://') or path_str.startswith('https://'):
            return path_str
        
        # 如果以 /static/ 开头，去掉前缀
        if path_str.startswith('/static/'):
            path_str = path_str[8:]
        
        # 如果是Windows绝对路径，提取相对路径部分
        if len(path_str) >= 3 and path_str[1] == ':':
            # 尝试找到 uploads 或 static 目录
            for marker in ['uploads/', 'static/']:
                idx = path_str.lower().find(marker)
                if idx != -1:
                    path_str = path_str[idx:]
                    break
            else:
                # 如果找不到标记，使用文件名
                path_str = os.path.basename(path_str)
        
        # 如果以 static/ 开头，去掉它（因为 url_for 会自动添加）
        if path_str.startswith('static/'):
            path_str = path_str[7:]
        
        try:
            return url_for('static', filename=path_str)
        except Exception:
            return f'/static/{path_str}'
    
    @app.template_filter('amount_in_words')
    def amount_in_words(amount, currency='SGD'):
        """将金额转换为英文大写形式"""
        try:
            amount = float(amount) if amount else 0
            
            # 数字到英文单词的映射
            ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
                   'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
                   'Seventeen', 'Eighteen', 'Nineteen']
            tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
            
            def num_to_words(n):
                if n < 20:
                    return ones[int(n)]
                elif n < 100:
                    return tens[int(n // 10)] + ('' if n % 10 == 0 else ' ' + ones[int(n % 10)])
                elif n < 1000:
                    return ones[int(n // 100)] + ' Hundred' + ('' if n % 100 == 0 else ' and ' + num_to_words(n % 100))
                elif n < 1000000:
                    return num_to_words(n // 1000) + ' Thousand' + ('' if n % 1000 == 0 else ' ' + num_to_words(n % 1000))
                else:
                    return num_to_words(n // 1000000) + ' Million' + ('' if n % 1000000 == 0 else ' ' + num_to_words(n % 1000000))
            
            # 分离整数和小数部分
            dollars = int(amount)
            cents = int(round((amount - dollars) * 100))
            
            # 货币名称映射
            currency_names = {
                'SGD': ('Singapore Dollars', 'Cents'),
                'USD': ('US Dollars', 'Cents'),
                'CNY': ('Chinese Yuan', 'Fen'),
                'MYR': ('Malaysian Ringgit', 'Sen'),
                'EUR': ('Euros', 'Cents'),
                'GBP': ('British Pounds', 'Pence')
            }
            
            dollar_name, cent_name = currency_names.get(currency, ('Dollars', 'Cents'))
            
            if dollars == 0 and cents == 0:
                return f"Zero {dollar_name} Only"
            
            result = ''
            if dollars > 0:
                result = num_to_words(dollars) + ' ' + dollar_name
            
            if cents > 0:
                if result:
                    result += ' and '
                result += num_to_words(cents) + ' ' + cent_name
            
            return result + ' Only'
        except Exception:
            return str(amount)

    # 注册设备检测上下文处理器
    @app.context_processor
    def inject_device_info():
        """注入设备类型信息到模板"""
        from .utils.device_detector import is_mobile, is_tablet, get_device_type
        return dict(
            is_mobile=is_mobile(),
            is_tablet=is_tablet(),
            device_type=get_device_type()
        )

    # 购物车数量上下文处理器
    @app.context_processor
    def inject_cart_count():
        def get_cart_count():
            from flask_login import current_user
            if current_user.is_authenticated:
                try:
                    from App_new.member.models.cart import CartItem
                    return CartItem.query.filter_by(user_id=current_user.id).count()
                except Exception:
                    return 0
            return 0
        return dict(cart_count=get_cart_count)

    # 注册应用级别的上下文处理器，让所有模板可以访问公司信息
    @app.context_processor
    def inject_company_info():
        def get_company_info():
            """获取公司信息（用于模板）"""
            try:
                from App_new.business.tour.models.Packagemodels import CompanyInfo
                from App_new.exts import db
                import os
                
                # 确保在应用上下文中
                if not hasattr(db, 'session'):
                    return None
                
                try:
                    company = CompanyInfo.query.first()
                    if not company:
                        return None
                    
                    # 处理logo_path
                    if company.logo_path:
                        try:
                            # 标准化路径并移除多余的前缀
                            path = str(company.logo_path).strip().replace('\\', '/')
                            original_path = path
                            
                            # 判断是否是URL路径（http://或https://开头）
                            is_url = path.startswith('http://') or path.startswith('https://')
                            
                            # 如果是URL路径，直接使用
                            if is_url:
                                company.logo_path = path
                            else:
                                # 移除可能存在的 'static/' 或 'App_new/static/' 前缀
                                if path.startswith('App_new/static/'):
                                    path = path[len('App_new/static/'):]
                                elif path.startswith('static/'):
                                    path = path[len('static/'):]
                                
                                # 判断是否是本地绝对路径
                                is_absolute = os.path.isabs(path)
                                
                                # 如果是本地绝对路径，检查文件是否存在
                                if is_absolute:
                                    if os.path.exists(path):
                                        # 文件存在，使用绝对路径（但需要通过file://协议或转换为相对路径）
                                        # 为了兼容性，尝试转换为相对于static的路径
                                        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'App_new', 'static')
                                        try:
                                            rel_path = os.path.relpath(path, static_dir).replace('\\', '/')
                                            if not rel_path.startswith('..'):
                                                path = rel_path
                                            else:
                                                # 如果无法转换为相对路径，保持绝对路径
                                                pass
                                        except:
                                            # 转换失败，保持绝对路径
                                            pass
                                    else:
                                        # 文件不存在，尝试作为相对路径处理
                                        is_absolute = False
                                
                                # 如果不是绝对路径，处理相对路径
                                if not is_absolute:
                                    # 如果路径不包含 'company/' 前缀，且不是绝对路径，且是纯文件名，则添加 'company/' 前缀
                                    if not path.startswith('company/') and not os.path.isabs(path):
                                        # 检查是否是文件名（不包含路径分隔符）
                                        if '/' not in path and '\\' not in path:
                                            path = 'company/' + path
                                
                                # 确保路径不为空
                                if path:
                                    company.logo_path = path
                                    company.logo_is_url = is_url
                                    company.logo_is_absolute = is_absolute
                        except Exception as path_error:
                            print(f"❌ 处理logo_path失败: {str(path_error)}")
                            import traceback
                            print(traceback.format_exc())
                            # 如果路径处理失败，保持原值
                            pass
                    
                    return company
                except Exception as query_error:
                    print(f"查询公司信息失败: {str(query_error)}")
                    return None
            except Exception as e:
                # 如果查询失败，返回None而不是抛出异常
                print(f"获取公司信息失败: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return None
        
        # 同时返回函数和直接值，确保兼容性
        company_info = get_company_info()
        return dict(
            get_company_info=get_company_info,
            company=company_info
        )

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
        from .business.projects.models.frequent_traveler import FrequentTraveler
        from .business.projects.models.traveler_file import TravelerFile
        from .finance.models.statement import (
            BankStatement, BankTransaction, SupplierStatement, SupplierStatementItem
        )
        # 银行关键词模型
        from .finance.models.bank_keywords import BankStatementKeyword, BankKeywordCategory
        # Athina账单模型已删除（数据已迁移到 ProjectHeader）
        # 会计科目与日记账模型
        from .finance.models.chart_of_account import ChartOfAccount
        from .finance.models.journal_entry import JournalEntry, JournalEntryLine
        from .finance.models.settlement_batch import SettlementBatch
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
            # Supplier 已合并到 CustomerCompany，保留导入用于向后兼容
            from .shared.models.Suppliers import Supplier  # 这是 CustomerCompany 的别名
            from .shared.models.Utilsmodels import Todo, TodoChecklist, TodoChecklistItem
            from .shared.models.contact_inquiry import ContactInquiry
        except Exception:
            pass
    except Exception:
        # 安静失败，不阻断应用启动
        pass
