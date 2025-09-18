# -*- coding: utf-8 -*-
"""邮件提醒模块"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app
from App_new.utils.reminder_utils import get_upcoming_reminders, mark_reminder_sent


def send_reminder_email(project_header, recipient_email):
    """
    发送项目提醒邮件
    
    Args:
        project_header: ProjectHeader实例
        recipient_email: 收件人邮箱
    """
    try:
        # 邮件配置
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = current_app.config.get('MAIL_PORT', 587)
        smtp_username = current_app.config.get('MAIL_USERNAME')
        smtp_password = current_app.config.get('MAIL_PASSWORD')
        
        if not smtp_username or not smtp_password:
            print("邮件配置不完整，无法发送提醒邮件")
            return False
        
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = recipient_email
        msg['Subject'] = f"项目提醒: {project_header.hid} - {project_header.reminder_event}"
        
        # 邮件正文
        body = f"""
尊敬的{project_header.staff_name}，

您有一个项目提醒即将到期：

项目编号: {project_header.hid}
项目描述: {project_header.desc}
提醒事件: {project_header.reminder_event}
提醒日期: {project_header.reminder_date.strftime('%Y-%m-%d') if project_header.reminder_date else '未设置'}
联系人: {project_header.contact}
公司: {project_header.company.company_name if project_header.company else '个人'}

请检查项目是否有变动，如有需要请及时更新项目信息。

此邮件由系统自动发送，请勿回复。

---
MyTravelPanel 系统
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_username, recipient_email, text)
        server.quit()
        
        print(f"提醒邮件发送成功: {project_header.hid} -> {recipient_email}")
        return True
        
    except Exception as e:
        print(f"发送提醒邮件失败: {e}")
        return False


def send_daily_reminders():
    """
    发送每日提醒邮件
    """
    try:
        # 获取即将到期的提醒（临时改为今天）
        upcoming_reminders = get_upcoming_reminders(days_ahead=0)
        
        if not upcoming_reminders:
            print("今日无项目提醒")
            return 0
        
        # 获取默认收件人邮箱列表
        default_emails = get_default_recipients()
        
        sent_count = 0
        for project in upcoming_reminders:
            # 获取经办人邮箱
            staff_email = None
            if project.staff_id:
                from App_new.auth.models import User
                staff_user = User.query.get(project.staff_id)
                if staff_user and staff_user.email:
                    staff_email = staff_user.email
            
            # 确定收件人列表
            if staff_email:
                # 如果经办人有邮箱，发送给经办人 + 默认收件人
                recipients = [staff_email] + default_emails
                recipients = list(set(recipients))  # 去重
            else:
                # 如果经办人无邮箱，只发送给默认收件人
                recipients = default_emails
            
            if recipients:
                success_count = 0
                for recipient in recipients:
                    if send_reminder_email(project, recipient):
                        success_count += 1
                        print(f"提醒邮件已发送: {project.hid} -> {recipient}")
                    else:
                        print(f"提醒邮件发送失败: {project.hid} -> {recipient}")
                
                if success_count > 0:
                    mark_reminder_sent(project)
                    sent_count += success_count
            else:
                print(f"无法获取项目 {project.hid} 的收件人邮箱")
        
        print(f"今日提醒邮件发送完成，共发送 {sent_count} 封")
        return sent_count
        
    except Exception as e:
        print(f"发送每日提醒失败: {e}")
        return 0


def get_default_recipients():
    """
    获取默认收件人邮箱列表
    """
    # 获取多个收件人配置（逗号分隔）
    recipients_str = current_app.config.get('DEFAULT_EMAIL_RECIPIENTS', '')
    if recipients_str:
        # 按逗号分割并去除空格
        recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
        return recipients
    
    # 如果没有配置多个收件人，使用单个默认收件人
    default_email = current_app.config.get('DEFAULT_EMAIL_RECIPIENT')
    if default_email:
        return [default_email]
    
    return []


def test_email_config():
    """
    测试邮件配置
    """
    try:
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = current_app.config.get('MAIL_PORT', 587)
        smtp_username = current_app.config.get('MAIL_USERNAME')
        smtp_password = current_app.config.get('MAIL_PASSWORD')
        
        if not smtp_username or not smtp_password:
            return False, "邮件配置不完整"
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.quit()
        
        return True, "邮件配置正常"
        
    except Exception as e:
        return False, f"邮件配置错误: {e}"
