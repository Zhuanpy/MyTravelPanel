# -*- coding: utf-8 -*-
"""邮件测试路由"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from App_new.utils.decorators import staff_only
from App_new.utils.email_reminder import test_email_config, send_reminder_email
from App_new.business.projects.models.project import ProjectHeader
from datetime import datetime, timedelta

email_test_bp = Blueprint('email_test', __name__, url_prefix='/utils/email-test')


@email_test_bp.route('/')
@login_required
@staff_only
def email_test_page():
    """邮件测试页面"""
    return render_template('utils/email_test.html')


@email_test_bp.route('/test-config', methods=['POST'])
@login_required
@staff_only
def test_config():
    """测试邮件配置"""
    try:
        success, message = test_email_config()
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }), 500


@email_test_bp.route('/send-test', methods=['POST'])
@login_required
@staff_only
def send_test_email():
    """发送测试邮件"""
    try:
        data = request.get_json()
        recipient_email = data.get('email')
        
        if not recipient_email:
            return jsonify({
                'success': False,
                'message': '请提供收件人邮箱'
            }), 400
        
        # 创建测试项目
        test_project = ProjectHeader(
            hid="TEST001",
            desc="邮件功能测试项目",
            reminder_event="系统邮件功能测试",
            reminder_date=datetime.now() + timedelta(days=1),
            staff_name="系统测试",
            contact="测试联系人"
        )
        
        # 发送测试邮件
        success = send_reminder_email(test_project, recipient_email)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'测试邮件已发送到 {recipient_email}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '邮件发送失败，请检查配置'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@email_test_bp.route('/check-config')
@login_required
@staff_only
def check_config():
    """检查邮件配置"""
    try:
        from flask import current_app
        
        config_info = {
            'MAIL_SERVER': current_app.config.get('MAIL_SERVER', '未设置'),
            'MAIL_PORT': current_app.config.get('MAIL_PORT', '未设置'),
            'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME', '未设置'),
            'MAIL_PASSWORD': '已设置' if current_app.config.get('MAIL_PASSWORD') else '未设置'
        }
        
        return jsonify({
            'success': True,
            'config': config_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查配置失败: {str(e)}'
        }), 500



