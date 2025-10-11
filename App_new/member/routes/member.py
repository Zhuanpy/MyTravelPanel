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
        # 导入订单模型
        from ..models.order import Order, OrderStatus
        
        # 获取会员统计信息
        total_orders = 0
        pending_orders = 0
        completed_orders = 0
        total_amount = 0
        
        try:
            # 查询当前用户的订单统计
            total_orders = Order.query.filter_by(user_id=current_user.id).count()
            pending_orders = Order.query.filter_by(user_id=current_user.id, status=OrderStatus.PENDING.value).count()
            completed_orders = Order.query.filter_by(user_id=current_user.id, status=OrderStatus.COMPLETED.value).count()
            
            # 计算总消费金额
            completed_orders_list = Order.query.filter_by(
                user_id=current_user.id, 
                status=OrderStatus.COMPLETED.value
            ).all()
            total_amount = sum(order.total_amount for order in completed_orders_list)
        except Exception as db_error:
            # 数据库表不存在时使用默认值
            pass
        
        stats = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'total_amount': total_amount,
        }
        
        # 获取最近的订单（最近5条）
        recent_orders = []
        try:
            recent_orders = Order.query.filter_by(user_id=current_user.id)\
                .order_by(Order.created_at.desc())\
                .limit(5)\
                .all()
        except Exception as db_error:
            # 数据库表不存在时使用空列表
            pass
        
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

# 订单功能已移至 orders.py 蓝图
# @member.route('/orders') - 已废弃，请使用 orders_bp 蓝图

# 订单详情功能已移至 orders.py 蓝图
# @member.route('/order/<int:order_id>') - 已废弃，请使用 orders_bp 蓝图

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
        # 暂时返回503，因为报价模型还未实现
        return render_template('member/error.html', 
                             title='功能建设中',
                             icon='tools',
                             color='info',
                             message='报价功能正在开发中，敬请期待',
                             show_back_button=True), 503
    except Exception as e:
        flash(f'加载报价详情失败：{str(e)}', 'error')
        return render_template('member/error.html',
                             title='加载失败',
                             icon='times-circle',
                             color='danger',
                             message='无法加载报价详情，请稍后再试',
                             details=str(e) if current_user.is_authenticated else None,
                             show_back_button=True), 500

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
        # 暂时返回503，因为发票模型还未实现
        return render_template('member/error.html',
                             title='功能建设中',
                             icon='tools',
                             color='info',
                             message='发票功能正在开发中，敬请期待',
                             show_back_button=True), 503
    except Exception as e:
        flash(f'加载发票详情失败：{str(e)}', 'error')
        return render_template('member/error.html',
                             title='加载失败',
                             icon='times-circle',
                             color='danger',
                             message='无法加载发票详情，请稍后再试',
                             details=str(e) if current_user.is_authenticated else None,
                             show_back_button=True), 500

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

# 服务申请功能已移至 orders.py

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