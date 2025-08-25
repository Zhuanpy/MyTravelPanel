"""
会员功能路由
会员仪表板、订单管理、报价查看等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from App.utils.decorators import member_only
from App.models.auth import AuthUser
from App.exts import db
from datetime import datetime, timedelta

# 创建会员蓝图
member = Blueprint('member', __name__, url_prefix='/member')

@member.route('/dashboard')
@login_required
@member_only
def dashboard():
    """会员仪表板"""
    try:
        # 获取会员统计信息
        stats = {
            'total_orders': 0,  # 总订单数
            'pending_orders': 0,  # 待处理订单
            'completed_orders': 0,  # 已完成订单
            'total_amount': 0,  # 总消费金额
        }
        
        # 获取最近的订单（暂时模拟数据）
        recent_orders = []
        
        # 获取最近的报价（暂时模拟数据）
        recent_quotes = []
        
        return render_template('member/member_dashboard.html',
                             stats=stats,
                             recent_orders=recent_orders,
                             recent_quotes=recent_quotes)
    except Exception as e:
        flash(f'加载仪表板失败：{str(e)}', 'error')
        return render_template('member/member_dashboard.html',
                             stats={}, recent_orders=[], recent_quotes=[])

@member.route('/orders')
@login_required
@member_only
def orders():
    """订单列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取订单状态筛选
        status = request.args.get('status', '')
        
        # 暂时返回空的订单列表
        orders = []
        pagination = None
        
        return render_template('member/orders.html',
                             orders=orders,
                             pagination=pagination,
                             current_status=status)
    except Exception as e:
        flash(f'加载订单列表失败：{str(e)}', 'error')
        return render_template('member/orders.html',
                             orders=[], pagination=None, current_status='')

@member.route('/order/<int:order_id>')
@login_required
@member_only
def order_detail(order_id):
    """订单详情"""
    try:
        # 暂时返回404，因为订单模型还未实现
        return render_template('member/404.html', message='订单功能暂未开放'), 404
    except Exception as e:
        flash(f'加载订单详情失败：{str(e)}', 'error')
        return render_template('member/404.html', message='加载失败'), 500

@member.route('/quotes')
@login_required
@member_only
def quotes():
    """报价列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取报价类型筛选
        quote_type = request.args.get('type', '')
        
        # 暂时返回空的报价列表
        quotes = []
        pagination = None
        
        return render_template('member/quotes.html',
                             quotes=quotes,
                             pagination=pagination,
                             current_type=quote_type)
    except Exception as e:
        flash(f'加载报价列表失败：{str(e)}', 'error')
        return render_template('member/quotes.html',
                             quotes=[], pagination=None, current_type='')

@member.route('/quote/<int:quote_id>')
@login_required
@member_only
def quote_detail(quote_id):
    """报价详情"""
    try:
        # 暂时返回404，因为报价模型还未实现
        return render_template('member/404.html', message='报价功能暂未开放'), 404
    except Exception as e:
        flash(f'加载报价详情失败：{str(e)}', 'error')
        return render_template('member/404.html', message='加载失败'), 500

@member.route('/invoices')
@login_required
@member_only
def invoices():
    """发票列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取发票状态筛选
        status = request.args.get('status', '')
        
        # 暂时返回空的发票列表
        invoices = []
        pagination = None
        
        return render_template('member/invoices.html',
                             invoices=invoices,
                             pagination=pagination,
                             current_status=status)
    except Exception as e:
        flash(f'加载发票列表失败：{str(e)}', 'error')
        return render_template('member/invoices.html',
                             invoices=[], pagination=None, current_status='')

@member.route('/invoice/<int:invoice_id>')
@login_required
@member_only
def invoice_detail(invoice_id):
    """发票详情"""
    try:
        # 暂时返回404，因为发票模型还未实现
        return render_template('member/404.html', message='发票功能暂未开放'), 404
    except Exception as e:
        flash(f'加载发票详情失败：{str(e)}', 'error')
        return render_template('member/404.html', message='加载失败'), 500

@member.route('/services')
@login_required
@member_only
def services():
    """可用服务"""
    try:
        # 获取可用的签证服务
        from App.models.Product.Visamodels import VisaTypes, VisaCountries
        
        visa_countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        # 按国家分组的签证服务
        services_by_country = {}
        for country in visa_countries:
            visa_types = VisaTypes.query.filter_by(country_id=country.id).order_by(VisaTypes.name).all()
            if visa_types:
                services_by_country[country] = visa_types
        
        return render_template('member/services.html',
                             services_by_country=services_by_country)
    except Exception as e:
        flash(f'加载服务列表失败：{str(e)}', 'error')
        return render_template('member/services.html',
                             services_by_country={})

@member.route('/service/apply/<visa_type>')
@login_required
@member_only
def apply_service(visa_type):
    """申请服务"""
    try:
        from App.models.Product.Visamodels import VisaTypes
        
        # 获取签证类型信息
        visa = VisaTypes.query.filter_by(name=visa_type).first()
        if not visa:
            return render_template('member/404.html', message='未找到该服务'), 404
        
        return render_template('member/apply_service.html', visa=visa)
    except Exception as e:
        flash(f'加载申请页面失败：{str(e)}', 'error')
        return render_template('member/404.html', message='加载失败'), 500

@member.route('/notifications')
@login_required
@member_only
def notifications():
    """通知中心"""
    try:
        # 暂时返回空的通知列表
        notifications = []
        
        return render_template('member/notifications.html',
                             notifications=notifications)
    except Exception as e:
        flash(f'加载通知失败：{str(e)}', 'error')
        return render_template('member/notifications.html',
                             notifications=[])

# API 路由
@member.route('/api/stats')
@login_required
@member_only
def api_stats():
    """获取会员统计数据"""
    try:
        stats = {
            'total_orders': 0,
            'pending_orders': 0,
            'completed_orders': 0,
            'total_amount': 0,
            'this_month_orders': 0,
            'this_month_amount': 0
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@member.route('/api/recent-activity')
@login_required
@member_only
def api_recent_activity():
    """获取最近活动"""
    try:
        activities = [
            {
                'type': 'order',
                'title': '欢迎加入MyTravelPanel',
                'description': '您的账户已激活，可以开始使用我们的服务',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'status': 'info'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': activities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 