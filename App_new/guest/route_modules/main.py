# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template, current_app
from App_new.business.tour.models.Packagemodels import CompanyInfo

# 创建主要页面蓝图
main_bp = Blueprint('main', __name__)

# 注意：首页路由 '/' 已移至 App_new/shared/routes/public.py
# 该文件中的 public 蓝图提供更完整的首页功能（包含旅游产品、签证国家、轮播图等）

@main_bp.route('/about')
def about():
    """关于我们页面"""
    # 从数据库获取公司信息
    db_company_info = CompanyInfo.query.first()
    
    company_info = {
        'name': db_company_info.company_name if db_company_info else 'MyTravelPanel',
        'description': db_company_info.company_description if db_company_info else '专业的旅游服务平台，致力于为客户提供优质的签证办理和旅游配套服务。',
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
    return render_template('guest/main/about.html', company=company_info, db_company=db_company_info)

@main_bp.route('/contact')
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
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM',  # 默认营业时间
            'languages': ['中文', 'English', 'Bahasa']  # 默认语言
        }
    else:
        # 默认联系信息
        contact_info = {
            'address': '新加坡市中心商业区',
            'phone': '+65 1234 5678',
            'email': 'info@joyesc.com',
            'wechat': 'MyTravelPanel',
            'business_hours': '周一至周五: 9:00 AM - 6:00 PM',
            'languages': ['中文', 'English', 'Bahasa']
        }
    
    return render_template('guest/main/contact.html', contact=contact_info, company=company_info)
