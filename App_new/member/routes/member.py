"""
会员功能路由
会员仪表板、订单管理、报价查看等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ...utils.decorators import member_only
from ...auth.models import AuthUser
from ...exts import db
from datetime import datetime, timedelta

# 创建会员蓝图
member = Blueprint('member', __name__, url_prefix='/member', template_folder='../templates')

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
        
        return render_template('member/dashboard.html', 
                             stats=stats,
                             recent_orders=recent_orders,
                             recent_quotes=recent_quotes)
    except Exception as e:
        flash(f'加载仪表板失败：{str(e)}', 'error')
        return render_template('member/dashboard.html',
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
                             current_type=quote_type,
                             now=datetime.now())
    except Exception as e:
        flash(f'加载报价列表失败：{str(e)}', 'error')
        return render_template('member/quotes.html',
                             quotes=[], pagination=None, current_type='',
                             now=datetime.now())

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
        # TODO: 需要创建签证相关的模型
        # 暂时使用模拟数据
        services_by_country = {
            '新加坡': [
                {'name': '旅游签证', 'processing_time': '3-5个工作日', 'price': 'SGD 50'},
                {'name': '商务签证', 'processing_time': '5-7个工作日', 'price': 'SGD 120'}
            ],
            '马来西亚': [
                {'name': '旅游签证', 'processing_time': '2-3个工作日', 'price': 'SGD 35'},
                {'name': '商务签证', 'processing_time': '3-5个工作日', 'price': 'SGD 80'}
            ],
            '泰国': [
                {'name': '旅游签证', 'processing_time': '3-5个工作日', 'price': 'SGD 40'}
            ]
        }
        
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
        # TODO: 需要创建签证相关的模型
        # 暂时使用模拟数据
        visa_info = {
            'name': visa_type,
            'description': f'{visa_type}申请服务',
            'processing_time': '3-5个工作日',
            'price': 'SGD 50',
            'required_documents': [
                '护照原件（有效期6个月以上）',
                '2张2寸白底彩色照片',
                '签证申请表',
                '往返机票预订单',
                '酒店预订单'
            ]
        }
        
        return render_template('member/apply_service.html', visa=visa_info)
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