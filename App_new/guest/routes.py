# -*- coding: utf-8 -*-
"""
访客/公开页面路由
提供公开的签证服务、旅游配套等信息浏览
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from ..utils.decorators import guest_only
from App_new.exts import cache
import logging

# 创建访客蓝图，指定模板文件夹
guest_bp = Blueprint('guest', __name__, 
                     template_folder='templates',
                     static_folder='../static/guest')

@guest_bp.route('/')
def index():
    """访客首页"""
    return render_template('guest/index.html')

@guest_bp.route('/visa-services')
def visa_services():
    """签证服务页面"""
    try:
        # TODO: 从数据库获取签证服务信息
        # 暂时使用模拟数据
        visa_services_data = [
            {
                'country': '新加坡',
                'country_en': 'Singapore',
                'services': ['旅游签证', '商务签证', '学生签证'],
                'processing_time': '3-5个工作日',
                'price_range': 'SGD 30-300'
            },
            {
                'country': '马来西亚',
                'country_en': 'Malaysia',
                'services': ['旅游签证', '商务签证'],
                'processing_time': '2-3个工作日',
                'price_range': 'SGD 35-250'
            },
            {
                'country': '泰国',
                'country_en': 'Thailand',
                'services': ['旅游签证', '商务签证'],
                'processing_time': '3-5个工作日',
                'price_range': 'SGD 40-280'
            }
        ]
        
        return render_template('guest/visa_services.html', 
                             visa_services=visa_services_data)
    except Exception as e:
        current_app.logger.error(f"加载签证服务页面失败: {e}")
        return render_template('guest/visa_services.html', 
                             visa_services=[])

@guest_bp.route('/visa-services/<country_name>')
def visa_services_by_country(country_name):
    """按国家查看签证服务"""
    try:
        # TODO: 根据国家名称从数据库获取具体信息
        # 暂时使用模拟数据
        country_visa_info = {
            'country': country_name,
            'description': f'{country_name}签证办理服务',
            'visa_types': [
                {
                    'name': '旅游签证',
                    'description': '适用于旅游、探亲访友',
                    'processing_time': '3-5个工作日',
                    'validity': '90天',
                    'price': 'SGD 50',
                    'required_documents': [
                        '护照原件（有效期6个月以上）',
                        '2张2寸白底彩色照片',
                        '签证申请表',
                        '往返机票预订单',
                        '酒店预订单'
                    ]
                },
                {
                    'name': '商务签证',
                    'description': '适用于商务考察、会议',
                    'processing_time': '5-7个工作日',
                    'validity': '90天',
                    'price': 'SGD 120',
                    'required_documents': [
                        '护照原件（有效期6个月以上）',
                        '2张2寸白底彩色照片',
                        '签证申请表',
                        '公司营业执照复印件',
                        '邀请函原件'
                    ]
                }
            ]
        }
        
        return render_template('guest/visa_services_country.html',
                             country_info=country_visa_info)
    except Exception as e:
        current_app.logger.error(f"加载国家签证服务失败: {e}")
        return render_template('guest/404.html', message='加载失败'), 500

@guest_bp.route('/visa-detail/<visa_type_name>')
def visa_detail(visa_type_name):
    """签证类型详情页面"""
    try:
        # TODO: 从数据库获取签证类型信息
        # 暂时使用模拟数据
        visa_detail_info = {
            'name': visa_type_name,
            'description': f'{visa_type_name}签证办理服务',
            'processing_time': '3-5个工作日',
            'validity': '90天',
            'price': 'SGD 50-300',
            'required_documents': [
                '护照原件（有效期6个月以上）',
                '2张2寸白底彩色照片',
                '签证申请表',
                '往返机票预订单',
                '酒店预订单'
            ],
            'notes': [
                '请确保护照有效期6个月以上',
                '建议提前2-3周申请',
                '材料齐全可提高通过率'
            ]
        }
        
        return render_template('guest/visa_detail.html',
                             visa_type=visa_detail_info)
    except Exception as e:
        current_app.logger.error(f"加载签证详情失败: {e}")
        return render_template('guest/404.html', message='加载失败'), 500

@guest_bp.route('/tour-packages')
def tour_packages():
    """旅游配套页面"""
    try:
        # TODO: 从数据库获取旅游配套信息
        # 暂时使用模拟数据
        tour_packages_data = [
            {
                'id': 1,
                'name': '新马泰经典7日游',
                'destination': '新加坡-马来西亚-泰国',
                'duration': '7天6夜',
                'price': 'SGD 1,280',
                'image': '/static/guest/images/tour1.jpg',
                'highlights': ['狮城风光', '吉隆坡双子塔', '曼谷大皇宫'],
                'includes': ['往返机票', '4星级酒店', '专业导游', '景点门票']
            },
            {
                'id': 2,
                'name': '巴厘岛浪漫5日游',
                'destination': '印尼巴厘岛',
                'duration': '5天4夜',
                'price': 'SGD 980',
                'image': '/static/guest/images/tour2.jpg',
                'highlights': ['乌布梯田', '海神庙', '蓝梦岛'],
                'includes': ['往返机票', '海景酒店', '专车接送', '特色餐饮']
            }
        ]
        
        return render_template('guest/tour_packages.html',
                             packages=tour_packages_data)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套页面失败: {e}")
        return render_template('guest/tour_packages.html', packages=[])

@guest_bp.route('/tour-package/<int:package_id>')
def tour_package_detail(package_id):
    """旅游配套详情页面"""
    try:
        # TODO: 根据package_id从数据库获取详细信息
        # 暂时使用模拟数据
        package_detail = {
            'id': package_id,
            'name': '新马泰经典7日游',
            'destination': '新加坡-马来西亚-泰国',
            'duration': '7天6夜',
            'price': 'SGD 1,280',
            'description': '体验东南亚三国的独特魅力，从现代化的新加坡到多元文化的马来西亚，再到充满异域风情的泰国。',
            'itinerary': [
                {'day': 1, 'title': '抵达新加坡', 'activities': ['机场接机', '入住酒店', '滨海湾花园']},
                {'day': 2, 'title': '新加坡市区游', 'activities': ['鱼尾狮公园', '牛车水', '小印度']},
                {'day': 3, 'title': '前往吉隆坡', 'activities': ['双子塔', '独立广场', '中央市场']},
                # ... 更多行程
            ],
            'includes': ['往返机票', '4星级酒店住宿', '专业中文导游', '景点门票', '部分餐饮'],
            'excludes': ['个人消费', '小费', '旅游保险', '签证费用'],
            'notes': ['请确保护照有效期6个月以上', '建议购买旅游保险', '行程可能因天气调整']
        }
        
        return render_template('guest/tour_package_detail.html',
                             package=package_detail)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套详情失败: {e}")
        return render_template('guest/404.html', message='加载失败'), 500

@guest_bp.route('/about')
def about():
    """关于我们页面"""
    company_info = {
        'name': 'MyTravelPanel',
        'description': '专业的旅游服务平台，致力于为客户提供优质的签证办理和旅游配套服务。',
        'established': '2020年',
        'services': [
            '签证办理服务',
            '旅游配套定制',
            '机票酒店预订',
            '旅游咨询服务'
        ],
        'advantages': [
            '专业团队，经验丰富',
            '服务范围覆盖全球',
            '高成功率，快速办理',
            '一对一客户服务'
        ]
    }
    return render_template('guest/about.html', company=company_info)

@guest_bp.route('/contact')
def contact():
    """联系我们页面"""
    contact_info = {
        'address': '新加坡市中心商业区',
        'phone': '+65 1234 5678',
        'email': 'info@mytravelpanel.com',
        'wechat': 'MyTravelPanel',
        'business_hours': '周一至周五: 9:00 AM - 6:00 PM',
        'languages': ['中文', 'English', 'Bahasa']
    }
    return render_template('guest/contact.html', contact=contact_info)

# API 接口
@guest_bp.route('/api/visa-countries')
def api_visa_countries():
    """API: 获取签证国家列表"""
    try:
        # TODO: 从数据库获取真实数据
        countries = [
            {'id': 1, 'name': '新加坡', 'name_en': 'Singapore', 'code': 'SG'},
            {'id': 2, 'name': '马来西亚', 'name_en': 'Malaysia', 'code': 'MY'},
            {'id': 3, 'name': '泰国', 'name_en': 'Thailand', 'code': 'TH'},
            {'id': 4, 'name': '印尼', 'name_en': 'Indonesia', 'code': 'ID'},
            {'id': 5, 'name': '越南', 'name_en': 'Vietnam', 'code': 'VN'}
        ]
        
        return jsonify({
            'success': True,
            'data': countries
        })
    except Exception as e:
        current_app.logger.error(f"获取签证国家列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

@guest_bp.route('/api/tour-packages')
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

# 错误处理
@guest_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('guest/404.html', message='页面未找到'), 404

@guest_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('guest/404.html', message='服务器内部错误'), 500