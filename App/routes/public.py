"""
访客功能路由
提供公开的签证服务、旅游配套等信息浏览
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from App.utils.decorators import guest_only
from App.models.Product.Visamodels import VisaTypes, VisaCountries
# from App.models.Product.PackageBudget import TourPackage  # 暂时注释，TourPackage类不存在
from App.exts import cache

# 创建访客蓝图
public = Blueprint('public', __name__, url_prefix='/public')

@public.route('/')
@guest_only
def index():
    """访客首页"""
    return render_template('public/index.html')

@public.route('/visa-services')
@guest_only
def visa_services():
    """签证服务页面"""
    try:
        # 获取所有签证国家
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        # 获取签证类型统计
        visa_stats = {}
        for country in countries:
            visa_count = VisaTypes.query.filter_by(country_id=country.id).count()
            if visa_count > 0:
                visa_stats[country.id] = visa_count
        
        return render_template('public/visa_services.html', 
                             countries=countries, 
                             visa_stats=visa_stats)
    except Exception as e:
        current_app.logger.error(f"加载签证服务页面失败: {e}")
        return render_template('public/visa_services.html', 
                             countries=[], 
                             visa_stats={})

@public.route('/visa-services/<country_name>')
@guest_only
def visa_services_by_country(country_name):
    """按国家查看签证服务"""
    try:
        # 获取国家信息（尝试中文和英文名称）
        country = VisaCountries.query.filter(
            (VisaCountries.country_name_CN == country_name) | 
            (VisaCountries.country_name_EN == country_name)
        ).first()
        
        if not country:
            return render_template('public/404.html', message='未找到该国家'), 404
        
        # 获取该国家的签证类型
        visa_types = VisaTypes.query.filter_by(country_id=country.id).order_by(VisaTypes.visa_type).all()
        
        return render_template('public/visa_services_country.html',
                             country=country,
                             visa_types=visa_types)
    except Exception as e:
        current_app.logger.error(f"加载国家签证服务失败: {e}")
        return render_template('public/404.html', message='加载失败'), 500

@public.route('/visa-detail/<visa_type_name>')
@guest_only
def visa_detail(visa_type_name):
    """签证类型详情页面"""
    try:
        # 获取签证类型信息
        visa_type = VisaTypes.query.filter_by(visa_type=visa_type_name).first()
        
        if not visa_type:
            return render_template('public/404.html', message='未找到该签证类型'), 404
        
        # 获取关联的身份信息
        identities = visa_type.identities if hasattr(visa_type, 'identities') else []
        
        # 获取文档配置信息
        document_data = {}
        if identities:
            from App.models.Product.Visamodels import VisaDocuments
            for identity in identities:
                doc_info = VisaDocuments.get_document_info(visa_type.id, identity.id)
                if doc_info:
                    document_data[identity.identity_zh] = doc_info
        
        return render_template('public/visa_detail.html',
                             visa_type=visa_type,
                             identities=identities,
                             document_data=document_data)
    except Exception as e:
        current_app.logger.error(f"加载签证详情失败: {e}")
        return render_template('public/404.html', message='加载失败'), 500

@public.route('/tour-packages')
@guest_only
def tour_packages():
    """旅游配套页面"""
    try:
        # 暂时返回空数据，因为TourPackage模型不存在
        packages_by_destination = {}
        
        return render_template('public/tour_packages.html',
                             packages_by_destination=packages_by_destination)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套页面失败: {e}")
        return render_template('public/tour_packages.html',
                             packages_by_destination={})

@public.route('/tour-package/<int:package_id>')
@guest_only
def tour_package_detail(package_id):
    """旅游配套详情页面"""
    try:
        # 暂时返回404，因为TourPackage模型不存在
        return render_template('public/404.html', message='旅游配套功能暂未开放'), 404
    except Exception as e:
        current_app.logger.error(f"加载旅游配套详情失败: {e}")
        return render_template('public/404.html', message='加载失败'), 500

@public.route('/about')
@guest_only
def about():
    """关于我们页面"""
    return render_template('public/about.html')

@public.route('/contact')
@guest_only
def contact():
    """联系我们页面"""
    return render_template('public/contact.html')

@public.route('/api/visa-countries')
@guest_only
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
@guest_only
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
@guest_only
def api_tour_packages():
    """API: 获取旅游配套列表"""
    try:
        # 暂时返回空数据，因为TourPackage模型不存在
        return jsonify({
            'success': True,
            'data': []
        })
    except Exception as e:
        current_app.logger.error(f"获取旅游配套列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500 