# -*- coding: utf-8 -*-
"""提醒管理路由"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from App_new.utils.decorators import staff_only
from App_new.utils.reminder_utils import sync_project_reminders, get_upcoming_reminders
from App_new.utils.email_reminder import send_daily_reminders, test_email_config
from App_new.business.projects.models.project import ProjectHeader
from datetime import datetime, timedelta

reminder_bp = Blueprint('reminder', __name__, url_prefix='/utils/reminders')


@reminder_bp.route('/')
@login_required
@staff_only
def reminder_dashboard():
    """提醒管理仪表板"""
    # 获取即将到期的提醒
    upcoming_reminders = get_upcoming_reminders(days_ahead=7)  # 未来7天
    
    # 获取所有有提醒的项目
    all_reminders = ProjectHeader.query.filter(
        ProjectHeader.reminder_event.isnot(None),
        ProjectHeader.reminder_date.isnot(None)
    ).order_by(ProjectHeader.reminder_date).all()
    
    return render_template('utils/reminder_dashboard.html', 
                         upcoming_reminders=upcoming_reminders,
                         all_reminders=all_reminders)


@reminder_bp.route('/sync', methods=['POST'])
@login_required
@staff_only
def sync_reminders():
    """同步项目提醒到待办事项"""
    try:
        count = sync_project_reminders()
        flash(f'同步完成，共同步 {count} 个项目提醒到待办事项', 'success')
    except Exception as e:
        flash(f'同步失败：{str(e)}', 'error')
    
    return redirect(url_for('reminder.reminder_dashboard'))


@reminder_bp.route('/send_test', methods=['POST'])
@login_required
@staff_only
def send_test_reminders():
    """发送测试提醒邮件"""
    try:
        count = send_daily_reminders()
        flash(f'测试邮件发送完成，共发送 {count} 封邮件', 'success')
    except Exception as e:
        flash(f'发送测试邮件失败：{str(e)}', 'error')
    
    return redirect(url_for('reminder.reminder_dashboard'))


@reminder_bp.route('/test_email_config', methods=['POST'])
@login_required
@staff_only
def test_email():
    """测试邮件配置"""
    try:
        success, message = test_email_config()
        if success:
            flash(f'邮件配置测试成功：{message}', 'success')
        else:
            flash(f'邮件配置测试失败：{message}', 'error')
    except Exception as e:
        flash(f'邮件配置测试失败：{str(e)}', 'error')
    
    return redirect(url_for('reminder.reminder_dashboard'))


@reminder_bp.route('/api/upcoming')
@login_required
@staff_only
def api_upcoming_reminders():
    """API: 获取即将到期的提醒"""
    try:
        days = request.args.get('days', 7, type=int)
        reminders = get_upcoming_reminders(days_ahead=days)
        
        result = []
        for reminder in reminders:
            result.append({
                'id': reminder.id,
                'hid': reminder.hid,
                'desc': reminder.desc,
                'reminder_event': reminder.reminder_event,
                'reminder_date': reminder.reminder_date.isoformat() if reminder.reminder_date else None,
                'contact': reminder.contact,
                'staff_name': reminder.staff_name,
                'company_name': reminder.company.company_name if reminder.company else '个人'
            })
        
        return jsonify({
            'success': True,
            'reminders': result,
            'count': len(result)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
