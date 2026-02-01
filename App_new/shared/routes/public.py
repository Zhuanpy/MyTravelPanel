"""
公开功能路由
提供所有用户都可以访问的签证服务、旅游配套等信息浏览
包括guest（未登录用户）、staff、admin等所有角色
"""

from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
from App_new.business.tour.models.Packagemodels import CompanyInfo, Product, TourProduct, ProductCity, HomeBanner
from App_new.exts import cache, db
from sqlalchemy import or_, and_
from datetime import date, datetime
import json


def is_mobile_device():
    """检测是否为移动设备"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

# 地区到国家的映射
REGION_COUNTRIES = {
    'southeast_asia': ['新加坡', '马来西亚', '泰国', '印尼', '印度尼西亚', '越南', '菲律宾', '柬埔寨', '老挝', '缅甸', '文莱'],
    'east_asia': ['日本', '韩国', '中国', '台湾', '香港', '澳门'],
    'europe': ['法国', '意大利', '德国', '英国', '西班牙', '瑞士', '荷兰', '希腊', '葡萄牙', '奥地利', '捷克', '匈牙利'],
    'america': ['美国', '加拿大', '墨西哥', '巴西', '阿根廷', '智利'],
    'oceania': ['澳大利亚', '新西兰', '斐济'],
    'middle_east': ['阿联酋', '土耳其', '埃及', '以色列', '约旦'],
    'south_asia': ['印度', '斯里兰卡', '马尔代夫', '尼泊尔']
}

# 创建访客蓝图
public = Blueprint('public', __name__, url_prefix='/public')

def get_company_info():
    """获取公司信息（用于模板）"""
    company = CompanyInfo.query.first()
    if company and company.logo_path:
        # 标准化路径并移除多余的前缀
        path = company.logo_path.replace('\\', '/')
        # 移除可能存在的 'static/' 或 'App_new/static/' 前缀
        path = path.replace('App_new/static/', '')
        path = path.replace('static/', '')
        company.logo_path = path
    return company

# 注册context processor，让所有模板可以访问公司信息
@public.app_context_processor
def inject_company_info():
    return dict(company=get_company_info())

@public.route('/')
def index():
    """公开首页 - 所有用户都可以访问"""
    # 手机端自动跳转到手机版首页
    if is_mobile_device():
        return redirect(url_for('mobile.public_home'))

    # 从数据库获取公司信息
    company_info = CompanyInfo.query.first()
    
    # 获取精选旅游产品（最多6个）
    today = date.today()
    tour_packages_query = Product.query.filter(
        or_(
            Product.product_status == 'active',
            Product.product_status.is_(None),
            Product.product_status == ''
        )
    ).order_by(Product.is_featured.desc(), Product.created_at.desc()).limit(6)
    
    tour_packages_raw = tour_packages_query.all()
    
    # 转换为模板需要的格式
    tour_packages = []
    for product in tour_packages_raw:
        # 格式化价格
        price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
        if product.currency and product.currency != 'SGD':
            price_display = f"{product.currency} {product.base_price:,.0f}" if product.base_price else "价格面议"
        
        # 格式化天数
        duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "天数待定"
        
        # 目的地显示
        destination_display = product.city_name or product.destination_city or "目的地待定"
        if product.country and product.country != '未知':
            destination_display = f"{product.country} · {destination_display}"
        
        tour_packages.append({
            'id': product.id,
            'name': product.product_name,
            'destination': destination_display,
            'duration': duration_display,
            'price': price_display,
            'image': product.cover_image,
            'is_featured': product.is_featured,
            'product_type': product.product_type
        })
    
    # 获取热门目的地（按产品数量统计）
    destinations_raw = db.session.query(
        ProductCity.country_name,
        db.func.count(Product.id).label('count')
    ).join(Product, Product.city_id == ProductCity.id).filter(
        or_(
            Product.product_status == 'active',
            Product.product_status.is_(None)
        )
    ).group_by(ProductCity.country_name).order_by(db.desc('count')).limit(8).all()
    
    destinations = [{'name': d[0], 'count': d[1]} for d in destinations_raw if d[0]]
    
    # 获取签证国家（有签证类型的国家）
    visa_countries_raw = db.session.query(
        VisaCountries.country_name_CN,
        VisaCountries.flag_file,
        db.func.count(VisaTypes.id).label('visa_count')
    ).join(VisaTypes, VisaTypes.country_id == VisaCountries.id).filter(
        VisaTypes.is_active == True
    ).group_by(VisaCountries.id).order_by(db.desc('visa_count')).limit(8).all()
    
    visa_countries = [{
        'name': vc[0],
        'flag': vc[1],
        'visa_count': vc[2]
    } for vc in visa_countries_raw]
    
    # 获取首页轮播图
    banners = HomeBanner.get_active_banners()
    
    return render_template('guest/main/index.html', 
                          company=company_info,
                          tour_packages=tour_packages,
                          destinations=destinations,
                          visa_countries=visa_countries,
                          banners=banners)

@public.route('/visa-services')
def visa_services():
    """签证服务页面"""
    # 手机端自动跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.visa_services', **request.args))

    try:
        # 获取筛选参数
        search_query = request.args.get('search', '').strip()
        region_filter = request.args.get('region', '').strip()
        
        # 获取所有签证国家
        countries_query = VisaCountries.query.order_by(VisaCountries.country_name_CN)
        
        # 应用搜索筛选
        if search_query:
            # 首先按国家名称搜索
            countries_query = countries_query.filter(
                (VisaCountries.country_name_CN.like(f'%{search_query}%')) |
                (VisaCountries.country_name_EN.like(f'%{search_query}%'))
            )
        
        countries = countries_query.all()
        
        # 如果搜索"申根"相关关键词，添加有申根签证的国家
        if search_query and any(keyword in search_query.lower() for keyword in ['申根', 'schengen']):
            all_countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
            for country in all_countries:
                visa_types = VisaTypes.query.filter_by(country_id=country.id, is_active=True).all()
                for visa_type in visa_types:
                    if any(keyword in visa_type.visa_type for keyword in ['申根', 'Schengen', 'schengen']):
                        if country not in countries:
                            countries.append(country)
                        break
        
        # 定义地区分类
        regions = {
            'asia': ['中国', '日本', '韩国', '新加坡', '马来西亚', '泰国', '越南', '印尼', '菲律宾', '印度', '斯里兰卡', '缅甸', '柬埔寨', '老挝', '文莱'],
            'europe': ['英国', '法国', '德国', '意大利', '西班牙', '荷兰', '瑞士', '奥地利', '比利时', '瑞典', '挪威', '丹麦', '芬兰', '波兰', '捷克', '匈牙利', '希腊', '葡萄牙', '申根', '申根签证', '申根国家'],
            'america': ['美国', '加拿大', '墨西哥', '巴西', '阿根廷', '智利', '秘鲁', '哥伦比亚', '委内瑞拉'],
            'oceania': ['澳大利亚', '新西兰', '斐济', '巴布亚新几内亚'],
            'africa': ['南非', '埃及', '摩洛哥', '肯尼亚', '坦桑尼亚', '埃塞俄比亚', '尼日利亚'],
            'middle_east': ['阿联酋', '沙特阿拉伯', '以色列', '土耳其', '伊朗', '伊拉克', '约旦', '黎巴嫩', '卡塔尔', '科威特', '巴林', '阿曼']
        }
        
        # 应用地区筛选
        if region_filter and region_filter in regions:
            region_countries = regions[region_filter]
            filtered_countries = []
            
            for country in countries:
                # 检查国家名称是否在地区列表中
                if country.country_name_CN in region_countries:
                    filtered_countries.append(country)
                else:
                    # 对于申根签证，检查是否有申根相关的签证类型
                    if region_filter == 'europe':
                        visa_types = VisaTypes.query.filter_by(country_id=country.id, is_active=True).all()
                        for visa_type in visa_types:
                            if any(keyword in visa_type.visa_type for keyword in ['申根', 'Schengen', 'schengen']):
                                filtered_countries.append(country)
                                break
            
            countries = filtered_countries
        
        # 获取签证类型统计
        visa_stats = {}
        for country in countries:
            visa_count = VisaTypes.query.filter_by(country_id=country.id, is_active=True).count()
            if visa_count > 0:
                visa_stats[country.id] = visa_count
        
        # 构建签证服务数据
        visa_services_data = []
        for country in countries:
            if country.id in visa_stats:
                # 获取该国家的签证类型
                visa_types = VisaTypes.query.filter_by(country_id=country.id).all()
                
                # 构建服务列表
                services = []
                min_fee = float('inf')
                max_fee = 0
                processing_times = []
                
                for visa_type in visa_types:
                    services.append(visa_type.visa_type)
                    
                    # 处理费用信息
                    if hasattr(visa_type, 'fee') and visa_type.fee:
                        try:
                            fee = float(visa_type.fee)
                            min_fee = min(min_fee, fee)
                            max_fee = max(max_fee, fee)
                        except (ValueError, TypeError):
                            pass
                    
                    # 处理时间信息
                    if hasattr(visa_type, 'processing_time') and visa_type.processing_time:
                        processing_times.append(visa_type.processing_time)
                
                # 构建价格范围
                if min_fee != float('inf') and max_fee > 0:
                    if min_fee == max_fee:
                        price_range = f'SGD {int(min_fee)}'
                    else:
                        price_range = f'SGD {int(min_fee)}-{int(max_fee)}'
                else:
                    price_range = None
                
                # 构建处理时间
                if processing_times:
                    unique_times = list(set(processing_times))
                    if len(unique_times) == 1:
                        processing_time = unique_times[0]
                    else:
                        processing_time = f'{unique_times[0]} 等'
                else:
                    processing_time = '时间面议'
                
                visa_services_data.append({
                    'country': country.country_name_CN,
                    'country_en': country.country_name_EN,
                    'country_code': country.country_code,
                    'flag_file': country.flag_file,
                    'services': services,
                    'processing_time': processing_time,
                    'price_range': price_range,
                    'visa_count': visa_stats[country.id]
                })
        
        # 准备地区选项数据
        region_options = {
            'asia': '亚洲',
            'europe': '欧洲', 
            'america': '美洲',
            'oceania': '大洋洲',
            'africa': '非洲',
            'middle_east': '中东'
        }
        
        # 获取公司信息
        company_info = CompanyInfo.query.first()
        
        return render_template('guest/visa/visa_services.html', 
                             visa_services=visa_services_data,
                             search_query=search_query,
                             region_filter=region_filter,
                             company=company_info,
                             region_options=region_options,
                             regions=regions)
    except Exception as e:
        current_app.logger.error(f"加载签证服务页面失败: {e}")
        # 获取公司信息
        company_info = CompanyInfo.query.first()
        
        return render_template('guest/visa/visa_services.html', 
                             visa_services=[],
                             search_query='',
                             region_filter='',
                             region_options={},
                             regions={},
                             company=company_info)

@public.route('/visa-services/<country_name>')
def visa_services_by_country(country_name):
    """按国家查看签证服务"""
    # 手机端自动跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.visa_country', country_name=country_name))

    try:
        # 获取国家信息（尝试中文和英文名称）
        country = VisaCountries.query.filter(
            (VisaCountries.country_name_CN == country_name) | 
            (VisaCountries.country_name_EN == country_name)
        ).first()
        
        if not country:
            return render_template('guest/shared/404.html', message='未找到该国家'), 404
        
        # 获取该国家的签证类型
        visa_types = VisaTypes.query.filter_by(country_id=country.id, is_active=True).order_by(VisaTypes.visa_type).all()
        
        # 转换为可序列化的格式
        visa_types_data = []
        for visa_type in visa_types:
            visa_types_data.append({
                'id': visa_type.id,
                'visa_type': visa_type.visa_type,
                'fee': visa_type.fee,
                'processing_time': visa_type.processing_time,
                'validity': getattr(visa_type, 'validity', None)
            })
        
        country_visa_info = {
            'country': country.country_name_CN,
            'country_en': country.country_name_EN,
            'country_code': country.country_code,
            'description': f'{country.country_name_CN}签证办理服务',
            'visa_types': visa_types_data  # 传递序列化后的数据
        }
        
        # 获取公司信息
        company_info = CompanyInfo.query.first()
        
        return render_template('guest/visa/visa_services_country.html',
                             country_info=country_visa_info,
                             company=company_info)
    except Exception as e:
        current_app.logger.error(f"加载国家签证服务失败: {e}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return render_template('guest/shared/404.html', message=f'加载失败: {str(e)}'), 500

@public.route('/visa-detail/<visa_type_name>')
def visa_detail(visa_type_name):
    """签证类型详情页面"""
    # 手机端自动跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.visa_detail', visa_type_name=visa_type_name))

    try:
        # 获取签证类型信息（只允许访问激活的）
        visa_type = VisaTypes.query.filter_by(visa_type=visa_type_name, is_active=True).first()
        
        if not visa_type:
            return render_template('guest/shared/404.html', message='未找到该签证类型'), 404
        
        # 记录访问统计
        try:
            from App_new.shared.services.visit_stats_service import VisitStatsService
            
            # 记录签证访问
            result = VisitStatsService.record_visa_visit(
                visa_type_id=visa_type.id,
                visa_type_name=visa_type.visa_type,
                country_name=visa_type.country.country_name_CN if visa_type.country else None
            )
            
            # 调试日志
            current_app.logger.info(f"访问统计记录结果: {result}")
            current_app.logger.info(f"签证类型ID: {visa_type.id}, 名称: {visa_type.visa_type}")
            
        except Exception as e:
            # 访问统计记录失败不影响页面正常显示
            current_app.logger.error(f"记录访问统计失败: {str(e)}")
            import traceback
            current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        
        # 获取关联的身份信息
        identities = visa_type.identities if hasattr(visa_type, 'identities') else []
        
        # 获取文档配置信息
        document_data = {}
        if identities:
            try:
                from App_new.business.visa.models.Visamodels import VisaDocuments
                for identity in identities:
                    doc_info = VisaDocuments.get_document_info(visa_type.id, identity.id)
                    if doc_info:
                        document_data[identity.identity_zh] = doc_info
            except ImportError as ie:
                current_app.logger.warning(f"无法导入VisaDocuments: {ie}")
                document_data = {}
        
        return render_template('guest/visa/visa_detail.html',
                             visa_type=visa_type,
                             identities=identities,
                             document_data=document_data)
    except Exception as e:
        current_app.logger.error(f"加载签证详情失败: {e}")
        return render_template('guest/shared/404.html', message='加载失败'), 500

@public.route('/tour-packages')
def tour_packages():
    """旅游配套页面"""
    # 手机端自动跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.tour_packages', **request.args))

    try:
        # 获取搜索参数
        destination = request.args.get('destination', '').strip()
        departure_date = request.args.get('departure_date', '')
        return_date = request.args.get('return_date', '')
        pax = request.args.get('pax', '')
        region = request.args.get('region', '')
        country = request.args.get('country', '').strip()
        city = request.args.get('city', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 12  # 每页显示12个产品
        
        # 构建查询
        # 先查询所有产品数量（用于调试）
        all_products_count = Product.query.count()
        active_products_count = Product.query.filter(Product.product_status == 'active').count()
        today = date.today()
        valid_products_count = Product.query.filter(
            Product.product_status == 'active'
        ).filter(
            or_(
                Product.valid_until.is_(None),
                Product.valid_until >= today
            )
        ).count()
        current_app.logger.info(f"数据库产品统计：总计 {all_products_count} 个，active状态 {active_products_count} 个，有效期内 {valid_products_count} 个")
        
        # 查询条件：active状态 或 状态为空（兼容旧数据）
        query = Product.query.filter(
            or_(
                Product.product_status == 'active',
                Product.product_status.is_(None),
                Product.product_status == ''
            )
        )
        
        # 标记是否需要join ProductCity
        need_join_city = False
        
        # 地区筛选
        if region and region in REGION_COUNTRIES:
            countries_in_region = REGION_COUNTRIES[region]
            # 构建地区筛选条件（Product.country是property，不能直接查询，需要通过ProductCity关联）
            region_conditions = []
            for country_name in countries_in_region:
                # 通过ProductCity的country_name筛选
                region_conditions.append(ProductCity.country_name.like(f'%{country_name}%'))
                # 也检查city_name和destination_city字段
                region_conditions.append(Product.city_name.like(f'%{country_name}%'))
                region_conditions.append(Product.destination_city.like(f'%{country_name}%'))
            # 通过ProductCity关联查询
            query = query.outerjoin(ProductCity, Product.city_id == ProductCity.id).filter(
                or_(*region_conditions)
            ).distinct()
            need_join_city = True
        
        # 国家筛选
        if country:
            # 通过ProductCity关联查询国家
            if not need_join_city:
                query = query.outerjoin(ProductCity, Product.city_id == ProductCity.id)
            query = query.filter(ProductCity.country_name == country).distinct()
        
        # 城市筛选
        if city:
            query = query.filter(Product.city_name == city)
        
        # 目的地筛选（关键词搜索，如果国家或城市已选择，则作为补充搜索）
        if destination:
            query = query.filter(
                or_(
                    Product.city_name.like(f'%{destination}%'),
                    Product.destination_city.like(f'%{destination}%')
                )
            )
        
        # 日期筛选（如果产品有有效期字段）
        today = date.today()
        if departure_date:
            try:
                dep_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
                query = query.filter(
                    or_(
                        Product.valid_from.is_(None),
                        Product.valid_from <= dep_date
                    )
                )
            except:
                pass
        
        if return_date:
            try:
                ret_date = datetime.strptime(return_date, '%Y-%m-%d').date()
                query = query.filter(
                    or_(
                        Product.valid_until.is_(None),
                        Product.valid_until >= ret_date
                    )
                )
            except:
                pass
        
        # 人数筛选
        if pax:
            try:
                if pax == '1':
                    min_pax = 1
                elif pax == '2':
                    min_pax = 2
                elif pax == '3-5':
                    min_pax = 3
                elif pax == '6-10':
                    min_pax = 6
                elif pax == '10+':
                    min_pax = 10
                else:
                    min_pax = None
                
                if min_pax:
                    query = query.filter(
                        or_(
                            Product.min_pax.is_(None),
                            Product.min_pax <= min_pax
                        )
                    )
            except:
                pass
        
        # 只显示有效的产品（有效期检查）
        # 注意：如果valid_until为None，表示永久有效
        # 如果valid_until已过期，仍然显示（可能用户需要查看历史产品）
        # 如果需要严格过滤过期产品，可以取消下面的注释
        # query = query.filter(
        #     or_(
        #         Product.valid_until.is_(None),
        #         Product.valid_until >= today
        #     )
        # )
        
        # 排序：精选优先，然后按创建时间倒序
        query = query.order_by(Product.is_featured.desc(), Product.created_at.desc())
        
        # 调试：记录查询总数
        total_count = query.count()
        current_app.logger.info(f"旅游配套查询：找到 {total_count} 个符合条件的active产品")
        
        # 分页
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        products = pagination.items
        current_app.logger.info(f"当前页显示 {len(products)} 个产品，共 {pagination.pages} 页，总计 {pagination.total} 个")
        
        # 转换为模板需要的格式
        packages = []
        for product in products:
            # 解析包含服务
            includes = []
            if product.included_services:
                try:
                    includes = json.loads(product.included_services) if product.included_services.startswith('[') else product.included_services.split(',')
                except:
                    includes = [i.strip() for i in product.included_services.split(',') if i.strip()]
            
            # 格式化价格
            price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
            if product.currency and product.currency != 'SGD':
                price_display = f"{product.currency} {product.base_price:,.0f}" if product.base_price else "价格面议"
            
            # 格式化天数
            duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "天数待定"
            
            # 目的地显示
            destination_display = product.city_name or product.destination_city or "目的地待定"
            if product.country and product.country != '未知':
                destination_display = f"{product.country} {destination_display}"
            
            packages.append({
                'id': product.id,
                'code': product.product_code or f'P{product.id:04d}',
                'name': product.product_name,
                'destination': destination_display,
                'duration': duration_display,
                'price': price_display,
                'image': product.cover_image if product.cover_image else None,
                'includes': includes[:4] if includes else ['专业导游', '优质服务']
            })
        
        # 获取国家和城市列表（用于下拉选择）
        countries = db.session.query(ProductCity.country_name).filter(
            ProductCity.country_name.isnot(None)
        ).distinct().order_by(ProductCity.country_name).all()
        countries = [c[0] for c in countries if c[0]]
        
        # 根据选择的国家获取城市列表
        cities = []
        if country:
            cities = db.session.query(ProductCity.city_name).filter(
                ProductCity.country_name == country,
                ProductCity.city_name.isnot(None)
            ).distinct().order_by(ProductCity.city_name).all()
            cities = [c[0] for c in cities if c[0]]
        else:
            # 如果没有选择国家，显示所有城市
            cities = db.session.query(Product.city_name).filter(
                Product.city_name.isnot(None)
            ).distinct().order_by(Product.city_name).all()
            cities = [c[0] for c in cities if c[0]]
        
        return render_template('guest/tour/tour_packages.html',
                             packages=packages,
                             pagination=pagination,
                             destination=destination,
                             departure_date=departure_date,
                             return_date=return_date,
                             pax=pax,
                             region=region,
                             country=country,
                             city=city,
                             countries=countries,
                             cities=cities,
                             regions=REGION_COUNTRIES)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套页面失败: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return render_template('guest/tour/tour_packages.html',
                             packages=[],
                             pagination=None)

@public.route('/tour-package/<int:package_id>')
def tour_package_detail(package_id):
    """旅游配套详情页面"""
    # 手机端自动跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.tour_package_detail', package_id=package_id))

    try:
        # 从Product模型查询产品详情
        product = Product.query.filter_by(id=package_id, product_status='active').first_or_404()
        
        # 检查产品是否有效
        today = date.today()
        if product.valid_until and product.valid_until < today:
            return render_template('guest/shared/404.html', message='该旅游配套已过期'), 404
        
        # 解析包含服务（可能是JSON或文本，支持换行和逗号分隔）
        includes = []
        if product.included_services:
            try:
                if product.included_services.startswith('['):
                    includes = json.loads(product.included_services)
                elif '\n' in product.included_services:
                    # 按换行分割
                    includes = [i.strip() for i in product.included_services.split('\n') if i.strip()]
                else:
                    # 按逗号分割
                    includes = [i.strip() for i in product.included_services.split(',') if i.strip()]
            except:
                includes = [i.strip() for i in product.included_services.split('\n') if i.strip()]

        # 解析不包含服务
        excludes = []
        if product.excluded_services:
            try:
                if product.excluded_services.startswith('['):
                    excludes = json.loads(product.excluded_services)
                elif '\n' in product.excluded_services:
                    # 按换行分割
                    excludes = [e.strip() for e in product.excluded_services.split('\n') if e.strip()]
                else:
                    # 按逗号分割
                    excludes = [e.strip() for e in product.excluded_services.split(',') if e.strip()]
            except:
                excludes = [e.strip() for e in product.excluded_services.split('\n') if e.strip()]
        
        # 解析注意事项
        notes = []
        if product.important_notes:
            try:
                notes = json.loads(product.important_notes) if product.important_notes.startswith('[') else product.important_notes.split('\n')
            except:
                notes = [n.strip() for n in product.important_notes.split('\n') if n.strip()]

        # 格式化价格
        price_display = f"SGD {product.base_price:,.0f}" if product.base_price else "价格面议"
        if product.currency and product.currency != 'SGD':
            price_display = f"{product.currency} {product.base_price:,.0f}" if product.base_price else "价格面议"
        
        # 格式化天数
        duration_display = f"{product.duration_days}天{product.duration_days-1 if product.duration_days else 0}夜" if product.duration_days else "天数待定"
        
        # 目的地显示
        destination_display = product.city_name or product.destination_city or "目的地待定"
        if product.country and product.country != '未知':
            destination_display = f"{product.country} {destination_display}"
        
        # 获取行程数据
        from App_new.business.tour.models.Packagemodels import ProductItinerary, ProductPriceVariant
        itineraries = ProductItinerary.query.filter_by(product_id=package_id).order_by(ProductItinerary.day_number).all()

        # 获取价格变体
        price_variants = ProductPriceVariant.query.filter_by(product_id=package_id, is_active=True).all()
        itinerary_list = []
        for it in itineraries:
            day_data = {
                'day': it.day_number,
                'title': it.day_title or f'第{it.day_number}天行程',
                'content': it.content,
                'activities': [it.content] if it.content else [],
                'images': [img for img in [it.image1, it.image2, it.image3] if img]
            }
            itinerary_list.append(day_data)
        
        # 准备产品详情数据
        package_data = {
            'id': product.id,
            'code': product.product_code or f'PKG-{product.id:04d}',
            'name': product.product_name,
            'destination': destination_display,
            'country': product.country,
            'duration': duration_display,
            'price': price_display,
            'child_price': f"{product.currency or 'SGD'} {product.child_price:,.0f}" if product.child_price else None,
            'image': product.cover_image,
            'description': product.product_description or '暂无详细描述，请联系我们的旅游顾问获取更多信息。',
            'includes': includes if includes else ['专业导游', '优质服务', '舒适住宿', '部分餐饮'],
            'excludes': excludes if excludes else ['个人消费', '小费', '旅游保险', '签证费用'],
            'notes': notes if notes else ['请确保护照有效期6个月以上', '建议购买旅游保险', '行程可能因天气调整'],
            'itinerary': itinerary_list if itinerary_list else None,
            'min_pax': product.min_pax,
            'max_pax': product.max_pax,
            'product_type': product.product_type,
            'supplier': product.display_company_name,
            'price_variants': [pv.to_dict() for pv in price_variants] if price_variants else [],
            'currency': product.currency or 'SGD'
        }

        # 获取公司联系信息
        company_info = CompanyInfo.query.first()

        return render_template('guest/tour/tour_package_detail.html', package=package_data, company=company_info)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套详情失败: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return render_template('guest/shared/404.html', message='加载失败'), 500

@public.route('/about')
def about():
    """关于我们页面"""
    return render_template('guest/main/about.html')

@public.route('/contact')
def contact():
    """联系我们页面"""
    # 移动设备跳转到手机版
    if is_mobile_device():
        return redirect(url_for('mobile.contact'))

    # 从数据库获取公司信息
    company_info = CompanyInfo.query.first()
    
    # 构建联系信息对象
    if company_info:
        contact_info = {
            'address': company_info.address,
            'phone': company_info.phone,
            'email': company_info.email,
            'wechat': 'MyTravelPanel',  # 默认微信
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM'  # 默认营业时间
        }
    else:
        # 默认联系信息
        contact_info = {
            'address': '新加坡市中心商业区',
            'phone': '+65 1234 5678',
            'email': 'info@joyesc.com',
            'wechat': 'MyTravelPanel',
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM'
        }
    
    return render_template('guest/main/contact.html', contact=contact_info)

@public.route('/api/visa-countries')
def api_visa_countries():
    """API: 获取签证国家列表"""
    try:
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        # 手动构建字典数据，因为模型可能没有to_dict方法
        country_data = []
        for country in countries:
            country_data.append({
                'id': country.id,
                'name': country.country_name_CN,
                'name_en': country.country_name_EN,
                'code': country.country_code
            })
        
        return jsonify({
            'success': True,
            'data': country_data
        })
    except Exception as e:
        current_app.logger.error(f"获取签证国家列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

@public.route('/api/visa-types/<int:country_id>')
def api_visa_types_by_country(country_id):
    """API: 获取指定国家的签证类型"""
    try:
        visa_types = VisaTypes.query.filter_by(country_id=country_id).order_by(VisaTypes.name).all()
        
        # 手动构建字典数据
        visa_type_data = []
        for visa_type in visa_types:
            visa_type_data.append({
                'id': visa_type.id,
                'name': visa_type.name,
                'fee': str(visa_type.fee) if hasattr(visa_type, 'fee') and visa_type.fee else '待定',
                'processing_time': visa_type.processing_time if hasattr(visa_type, 'processing_time') else '待定'
            })
        
        return jsonify({
            'success': True,
            'data': visa_type_data
        })
    except Exception as e:
        current_app.logger.error(f"获取签证类型失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

@public.route('/api/tour-packages')
def api_tour_packages():
    """API: 获取旅游配套列表"""
    try:
        # TODO: 从数据库获取真实数据
        packages = [
            {
                'id': 1,
                'name': '新马泰经典7日游',
                'price': 1280,
                'duration': 7,
                'destination': '新加坡-马来西亚-泰国'
            },
            {
                'id': 2,
                'name': '巴厘岛浪漫5日游',
                'price': 980,
                'duration': 5,
                'destination': '印尼巴厘岛'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': packages
        })
    except Exception as e:
        current_app.logger.error(f"获取旅游配套列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

# 添加guest模块中的额外API功能
@public.route('/api/get_identity_options/<visa_type>')
def get_identity_options(visa_type):
    """获取签证类型的身份选项"""
    try:
        from urllib.parse import unquote
        import html
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaSingaporeIdentity, VisaDocuments
        
        # URL解码签证类型
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        # 验证签证类型是否存在
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': f'签证类型 {decoded_visa_type} 不存在',
                'identity_options': []
            }), 404
        
        # 从visa_type_identities表获取该签证类型关联的身份选项
        visa_type_identities = visa_type_record.identities
        identity_options = [identity.identity_zh for identity in visa_type_identities]
        
        # 确保SHARE在第一位（如果存在）
        if 'SHARE' in identity_options:
            identity_options.remove('SHARE')
            identity_options.insert(0, 'SHARE')
        
        return jsonify({
            'success': True,
            'identity_options': identity_options
        })
    except Exception as e:
        current_app.logger.error(f"获取身份选项失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'identity_options': []
        }), 500

@public.route('/api/get_visa_documents/<visa_type>/<identity>')
def get_visa_documents(visa_type, identity):
    """获取指定签证类型和身份的文档资料"""
    try:
        from urllib.parse import unquote
        import html
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaSingaporeIdentity, VisaDocuments
        
        # URL解码参数
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        decoded_identity = unquote(identity)
        decoded_identity = html.unescape(decoded_identity)
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 404
        
        # 获取申请人准备的文档信息
        if decoded_identity == 'SHARE':
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
            if identity_record:
                documents_info = VisaDocuments.get_applicant_documents(visa_type_record.id, identity_record.id)
            else:
                documents_info = {'document_info': '暂无文件资料', 'additional_info': '暂无补充信息'}
        else:
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=decoded_identity).first()
            if identity_record:
                documents_info = VisaDocuments.get_applicant_documents(visa_type_record.id, identity_record.id)
            else:
                documents_info = {'document_info': '暂无文件资料', 'additional_info': '暂无补充信息'}
        
        return jsonify({
            'success': True,
            'document_info': documents_info.get('document_info', '暂无文件资料'),
            'additional_info': documents_info.get('additional_info', '暂无补充信息'),
            'applicant_additional_info': documents_info.get('applicant_additional_info', '暂无申请人补充信息')
        })
    except Exception as e:
        current_app.logger.error(f"获取签证文档失败: {e}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }), 500


@public.route('/attractions')
def attractions():
    """景点门票 - 即将推出占位页面"""
    company_info = CompanyInfo.query.first()
    return render_template('guest/attractions/coming_soon.html', company=company_info)