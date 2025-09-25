# -*- coding: utf-8 -*-
"""
旅游配套相关路由
"""

from flask import Blueprint, render_template, current_app

# 创建旅游蓝图
tour_bp = Blueprint('tour', __name__)

@tour_bp.route('/tour-packages')
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
        
        return render_template('guest/tour/tour_packages.html',
                             packages=tour_packages_data)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套页面失败: {e}")
        return render_template('guest/tour/tour_packages.html', packages=[])

@tour_bp.route('/tour-package/<int:package_id>')
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
        
        return render_template('guest/tour/tour_package_detail.html',
                             package=package_detail)
    except Exception as e:
        current_app.logger.error(f"加载旅游配套详情失败: {e}")
        return render_template('guest/shared/404.html', message='加载失败'), 500
