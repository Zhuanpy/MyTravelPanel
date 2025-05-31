from flask import Blueprint, render_template, request, redirect, url_for
from ..models import VisaTypes

"""
签证首页 (visa_home.py):
显示签证首页 (/visa/home)
提供快速导航

"""

visa_home = Blueprint('visa_home', __name__)

@visa_home.route('/visa_home')
@visa_home.route('/')
def home():
    """签证首页路由"""
    # 获取所有签证类别
    visa_categories = VisaTypes.query.all()
    
    # 在后端进行分组处理
    visas_by_country = {}
    for visa in visa_categories:
        country_name = visa.country.country_name_CN
        if country_name not in visas_by_country:
            visas_by_country[country_name] = []
        visas_by_country[country_name].append(visa)

    return render_template('visas/签证首页.html',
                         visa_categories=visa_categories,
                         visas_by_country=visas_by_country)

