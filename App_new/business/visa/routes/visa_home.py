from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from App_new.business.visa.models.Visamodels import VisaTypes
from App_new.utils.decorators import staff_only

"""
签证首页 (visa_home.py):
显示签证首页 (/visa/home)
提供快速导航

"""

visa_home = Blueprint('visa_home', __name__)

@visa_home.route('/visa_home')
@visa_home.route('/')
@login_required
@staff_only
def home():
    """签证首页路由"""
    # 获取所有签证类别（只显示激活的）
    visa_categories = VisaTypes.query.filter_by(is_active=True).all()
    
    # 在后端进行分组处理
    visas_by_country = {}
    for visa in visa_categories:
        country_name = visa.country.country_name_CN
        if country_name not in visas_by_country:
            visas_by_country[country_name] = []
        visas_by_country[country_name].append(visa)

    return render_template('business/visa/签证首页.html',
                         visas_by_country=visas_by_country)

