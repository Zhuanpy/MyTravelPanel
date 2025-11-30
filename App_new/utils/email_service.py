# -*- coding: utf-8 -*-
"""
邮件服务模块
用于发送各类系统邮件
"""

from flask import current_app
from flask_mail import Mail, Message


def send_password_reset_email(to_email, username, reset_url):
    """
    发送密码重置邮件
    
    Args:
        to_email: 收件人邮箱
        username: 用户名
        reset_url: 密码重置链接
    """
    try:
        mail = Mail(current_app)
        
        # 从Flask配置中获取发件人信息
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME', 'noreply@mytravelpanel.com')
        sender_str = f"MyTravelPanel <{sender_email}>"
        
        print(f"[邮件服务] 准备发送密码重置邮件到: {to_email}")
        print(f"[邮件服务] 发件人: {sender_str}")
        print(f"[邮件服务] MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")
        
        subject = '【MyTravelPanel】密码重置请求'
        
        # HTML邮件内容
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #3498db, #2c3e50);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #27ae60, #3498db);
                    color: white !important;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .button:hover {{
                    opacity: 0.9;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #888;
                    font-size: 12px;
                    padding: 20px;
                    border-top: 1px solid #ddd;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔐 密码重置</h1>
            </div>
            <div class="content">
                <p>尊敬的 <strong>{username}</strong>，您好！</p>
                
                <p>我们收到了您的密码重置请求。请点击下面的按钮来重置您的密码：</p>
                
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">重置我的密码</a>
                </p>
                
                <div class="warning">
                    <p><strong>⚠️ 安全提示：</strong></p>
                    <ul>
                        <li>此链接将在 <strong>1小时</strong> 后失效</li>
                        <li>如果您没有请求重置密码，请忽略此邮件</li>
                        <li>请勿将此链接分享给他人</li>
                    </ul>
                </div>
                
                <p>如果按钮无法点击，请复制以下链接到浏览器中访问：</p>
                <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px;">
                    {reset_url}
                </p>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2024 MyTravelPanel. All rights reserved.</p>
            </div>
        </body>
        </html>
        '''
        
        # 纯文本邮件内容（作为备用）
        text_body = f'''
尊敬的 {username}，您好！

我们收到了您的密码重置请求。

请访问以下链接来重置您的密码：
{reset_url}

安全提示：
- 此链接将在1小时后失效
- 如果您没有请求重置密码，请忽略此邮件
- 请勿将此链接分享给他人

此邮件由系统自动发送，请勿直接回复。

© 2024 MyTravelPanel. All rights reserved.
        '''
        
        msg = Message(
            subject=subject,
            sender=sender_str,
            recipients=[to_email],
            body=text_body,
            html=html_body
        )
        
        mail.send(msg)
        print(f"密码重置邮件发送成功: {to_email}")
        return True
        
    except Exception as e:
        print(f"发送密码重置邮件失败: {str(e)}")
        raise


def send_verification_email(to_email, username, verification_code):
    """
    发送邮箱验证码邮件
    
    Args:
        to_email: 收件人邮箱
        username: 用户名
        verification_code: 验证码
    """
    try:
        mail = Mail(current_app)
        mail_config = current_app.config.get('MAIL_CONFIG', {})
        
        sender = mail_config.get('DEFAULT_SENDER', {})
        sender_email = sender.get('email', 'noreply@mytravelpanel.com')
        sender_name = sender.get('name', 'MyTravelPanel')
        sender_str = f"{sender_name} <{sender_email}>"
        
        subject = '【MyTravelPanel】邮箱验证码'
        
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #3498db, #2c3e50);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #3498db;
                    text-align: center;
                    letter-spacing: 8px;
                    padding: 20px;
                    background: #fff;
                    border-radius: 8px;
                    border: 2px dashed #3498db;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #888;
                    font-size: 12px;
                    padding: 20px;
                    border-top: 1px solid #ddd;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📧 邮箱验证</h1>
            </div>
            <div class="content">
                <p>尊敬的 <strong>{username}</strong>，您好！</p>
                
                <p>您的邮箱验证码是：</p>
                
                <div class="code">{verification_code}</div>
                
                <p>验证码有效期为 <strong>10分钟</strong>，请尽快使用。</p>
                
                <p>如果您没有请求此验证码，请忽略此邮件。</p>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2024 MyTravelPanel. All rights reserved.</p>
            </div>
        </body>
        </html>
        '''
        
        text_body = f'''
尊敬的 {username}，您好！

您的邮箱验证码是：{verification_code}

验证码有效期为10分钟，请尽快使用。

如果您没有请求此验证码，请忽略此邮件。

此邮件由系统自动发送，请勿直接回复。

© 2024 MyTravelPanel. All rights reserved.
        '''
        
        msg = Message(
            subject=subject,
            sender=sender_str,
            recipients=[to_email],
            body=text_body,
            html=html_body
        )
        
        mail.send(msg)
        print(f"验证码邮件发送成功: {to_email}")
        return True
        
    except Exception as e:
        print(f"发送验证码邮件失败: {str(e)}")
        raise

