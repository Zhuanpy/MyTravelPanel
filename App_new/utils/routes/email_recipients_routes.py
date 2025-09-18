# -*- coding: utf-8 -*-
"""邮件收件人管理路由"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from App_new.utils.decorators import staff_only
from App_new.utils.email_reminder import get_default_recipients, send_reminder_email
from App_new.business.projects.models.project import ProjectHeader
from datetime import datetime, timedelta

email_recipients_bp = Blueprint('email_recipients', __name__, url_prefix='/utils/email-recipients')


@email_recipients_bp.route('/')
@login_required
@staff_only
def recipients_management():
    """邮件收件人管理页面"""
    # 获取当前收件人列表
    current_recipients = get_default_recipients()
    
    return render_template('utils/email_recipients.html', 
                         recipients=current_recipients)


@email_recipients_bp.route('/test-send', methods=['POST'])
@login_required
@staff_only
def test_send_to_recipients():
    """测试发送邮件给所有收件人"""
    try:
        data = request.get_json()
        test_message = data.get('message', '测试邮件')
        
        # 获取收件人列表
        recipients = get_default_recipients()
        
        if not recipients:
            return jsonify({
                'success': False,
                'message': '没有配置收件人邮箱'
            }), 400
        
        # 创建测试项目
        test_project = ProjectHeader(
            hid="TEST001",
            desc="邮件收件人测试项目",
            reminder_event=test_message,
            reminder_date=datetime.now() + timedelta(days=1),
            staff_name="系统测试",
            contact="测试联系人"
        )
        
        # 发送测试邮件给所有收件人
        success_count = 0
        failed_recipients = []
        
        for recipient in recipients:
            if send_reminder_email(test_project, recipient):
                success_count += 1
            else:
                failed_recipients.append(recipient)
        
        return jsonify({
            'success': True,
            'message': f'测试邮件发送完成，成功: {success_count}，失败: {len(failed_recipients)}',
            'failed_recipients': failed_recipients
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@email_recipients_bp.route('/get-recipients')
@login_required
@staff_only
def get_recipients():
    """获取当前收件人列表"""
    try:
        recipients = get_default_recipients()
        return jsonify({
            'success': True,
            'recipients': recipients
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取收件人失败: {str(e)}'
        }), 500



