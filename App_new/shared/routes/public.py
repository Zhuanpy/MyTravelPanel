"""
公开功能路由
提供所有用户都可以访问的签证服务、旅游配套等信息浏览
包括guest（未登录用户）、staff、admin等所有角色
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
from App_new.business.tour.models.Packagemodels import CompanyInfo
# from App.models.Product.PackageBudget import TourPackage  # 暂时注释，TourPackage类不存在
from App_new.exts import cache

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
    # 从数据库获取公司信息
    company_info = CompanyInfo.query.first()
    return render_template('guest/main/index.html', company=company_info)

@public.route('/visa-services')
def visa_services():
    """签证服务页面"""
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
    try:
        # 暂时返回空数据，因为TourPackage模型不存在
        packages_by_destination = {}
        
        return render_template('guest/tour/tour_packages.html',
                             packages=packages_by_destination)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套页面失败: {e}")
        return render_template('guest/tour/tour_packages.html',
                             packages={})

@public.route('/tour-package/<int:package_id>')
def tour_package_detail(package_id):
    """旅游配套详情页面"""
    try:
        # 暂时返回404，因为TourPackage模型不存在
        return render_template('guest/shared/404.html', message='旅游配套功能暂未开放'), 404
    except Exception as e:
        current_app.logger.error(f"加载旅游配套详情失败: {e}")
        return render_template('guest/shared/404.html', message='加载失败'), 500

@public.route('/about')
def about():
    """关于我们页面"""
    return render_template('guest/main/about.html')

@public.route('/contact')
def contact():
    """联系我们页面"""
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