# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template, current_app

# 创建主要页面蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """访客首页"""
    return render_template('guest/main/index.html')

@main_bp.route('/about')
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
    return render_template('guest/main/about.html', company=company_info)

@main_bp.route('/contact')
def contact():
    """联系我们页面"""
    contact_info = {
        'address': '新加坡市中心商业区',
        'phone': '+65 1234 5678',
        'email': 'info@joyesc.com',
        'wechat': 'MyTravelPanel',
        'business_hours': '周一至周五: 9:00 AM - 6:00 PM',
        'languages': ['中文', 'English', 'Bahasa']
    }
    return render_template('guest/main/contact.html', contact=contact_info)
