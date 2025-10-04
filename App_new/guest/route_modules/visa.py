# -*- coding: utf-8 -*-
"""
签证相关路由
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from urllib.parse import unquote
import html
from App_new.business.tour.models.Packagemodels import CompanyInfo

# 创建签证蓝图
visa_bp = Blueprint('visa', __name__)

@visa_bp.route('/visa-services')
def visa_services():
    """签证服务页面"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
        
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
        
        # 调试：检查申根签证数据
        if request.args.get('debug') == 'schengen':
            schengen_countries = []
            all_countries = VisaCountries.query.all()
            for country in all_countries:
                visa_types = VisaTypes.query.filter_by(country_id=country.id).all()
                for visa_type in visa_types:
                    if any(keyword in visa_type.visa_type for keyword in ['申根', 'Schengen', 'schengen']):
                        schengen_countries.append({
                            'country': country.country_name_CN,
                            'visa_type': visa_type.visa_type
                        })
            print(f"DEBUG: Found {len(schengen_countries)} Schengen visa types:")
            for item in schengen_countries:
                print(f"  - {item['country']}: {item['visa_type']}")
        
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

@visa_bp.route('/visa-services/<country_name>')
def visa_services_by_country(country_name):
    """按国家查看签证服务"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries, VisaDocuments, VisaSingaporeIdentity
        
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

@visa_bp.route('/visa-detail/<visa_type_name>')
def visa_detail(visa_type_name):
    """签证类型详情页面"""
    try:
        current_app.logger.info(f"开始处理签证详细页面请求: {visa_type_name}")
        
        # 首先测试基本的导入和查询
        try:
            from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries, VisaDocuments, VisaSingaporeIdentity
            current_app.logger.info("成功导入签证模型")
        except Exception as me:
            current_app.logger.error(f"导入签证模型失败: {str(me)}")
            return f"Model Import Error: {str(me)}", 500
        
        # URL解码参数
        try:
            decoded_visa_type = unquote(visa_type_name)
            decoded_visa_type = html.unescape(decoded_visa_type)
            current_app.logger.info(f"解码后的签证类型: {decoded_visa_type}")
        except Exception as de:
            current_app.logger.error(f"URL解码失败: {str(de)}")
            return f"Decode Error: {str(de)}", 500
        
        # 获取签证类型信息
        try:
            visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type, is_active=True).first()
            current_app.logger.info(f"查询签证类型结果: {visa_type_record}")
        except Exception as qe:
            current_app.logger.error(f"查询签证类型失败: {str(qe)}")
            return f"Query Error: {str(qe)}", 500
        
        if not visa_type_record:
            # 获取所有签证类型用于错误提示
            try:
                all_visa_types = VisaTypes.query.all()
                available_types = [vt.visa_type for vt in all_visa_types]
                current_app.logger.error(f"未找到签证类型: {decoded_visa_type}")
                current_app.logger.error(f"可用的签证类型: {available_types}")
                return render_template('guest/shared/404.html', 
                                     message=f'签证类型不存在: {decoded_visa_type}。可用的类型: {", ".join(available_types)}'), 404
            except Exception as ae:
                current_app.logger.error(f"获取所有签证类型失败: {str(ae)}")
                return f"Get All Types Error: {str(ae)}", 500
        
        # 记录访问统计
        try:
            from App_new.shared.services.visit_stats_service import VisitStatsService
            
            # 记录签证访问
            result = VisitStatsService.record_visa_visit(
                visa_type_id=visa_type_record.id,
                visa_type_name=visa_type_record.visa_type,
                country_name=visa_type_record.country.country_name_CN if visa_type_record.country else None
            )
            
            # 调试日志
            current_app.logger.info(f"访问统计记录结果: {result}")
            current_app.logger.info(f"签证类型ID: {visa_type_record.id}, 名称: {visa_type_record.visa_type}")
            
        except Exception as e:
            # 访问统计记录失败不影响页面正常显示
            current_app.logger.error(f"记录访问统计失败: {str(e)}")
            import traceback
            current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")

        # 获取国家信息
        try:
            country = VisaCountries.query.get(visa_type_record.country_id)
            current_app.logger.info(f"获取国家信息: {country}")
        except Exception as ce:
            current_app.logger.error(f"获取国家信息失败: {str(ce)}")
            country = None
        
        # 获取身份选项
        try:
            identities = []
            if visa_type_record.identities:
                identities = [identity.identity_zh for identity in visa_type_record.identities]
            current_app.logger.info(f"获取身份选项: {identities}")
        except Exception as ie:
            current_app.logger.error(f"获取身份选项失败: {str(ie)}")
            identities = []
        
        # 简化：暂时不获取文档信息，先让页面能正常显示
        applicant_documents = []
        
        # 构建签证详情信息
        try:
            visa_detail_info = {
                'name': visa_type_record.visa_type,
                'country': country.country_name_CN if country else '未知国家',
                'description': f'{visa_type_record.visa_type}签证办理服务',
                'processing_time': visa_type_record.processing_time or '3-5个工作日',
                'fee': visa_type_record.fee or '请咨询',
                'introduction': visa_type_record.introduction or '',
                'required_documents': applicant_documents,
                'identities': identities,
                'additional_info': ''
            }
            current_app.logger.info(f"构建签证详情信息成功: {visa_detail_info['name']}")
        except Exception as ve:
            current_app.logger.error(f"构建签证详情信息失败: {str(ve)}")
            return f"Build Visa Info Error: {str(ve)}", 500
        
        # 渲染模板
        try:
            # 获取公司信息
            company_info = CompanyInfo.query.first()
            
            return render_template('guest/visa/visa_detail.html', 
                                 visa_type=visa_detail_info,
                                 company=company_info)
        except Exception as te:
            current_app.logger.error(f"渲染模板失败: {str(te)}")
            return f"Template Render Error: {str(te)}", 500
    except Exception as e:
        current_app.logger.error(f"加载签证详情失败: {e}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return render_template('guest/shared/404.html', message='加载失败'), 500
