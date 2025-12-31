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
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME', 'noreply@joyesc.com')
        sender_str = f"悦行假期 Joyeful Escapes <{sender_email}>"

        print(f"[邮件服务] 准备发送密码重置邮件到: {to_email}")
        print(f"[邮件服务] 发件人: {sender_str}")
        print(f"[邮件服务] MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")

        subject = '【悦行假期】密码重置请求'

        # HTML邮件内容 - 绿色会员风格
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <tr>
                    <td style="background: linear-gradient(135deg, #28a745 0%, #34ce57 100%); padding: 40px 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <div style="width: 70px; height: 70px; background: rgba(255,255,255,0.2); border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                            <span style="font-size: 32px;">🔐</span>
                        </div>
                        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">密码重置</h1>
                        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0; font-size: 14px;">悦行假期 Joyeful Escapes</p>
                    </td>
                </tr>

                <!-- Content -->
                <tr>
                    <td style="padding: 40px 30px; background-color: #ffffff; border-left: 1px solid #e9ecef; border-right: 1px solid #e9ecef;">
                        <p style="color: #333; font-size: 16px; margin: 0 0 20px;">尊敬的 <strong>{username}</strong>，您好！</p>

                        <p style="color: #666; font-size: 15px; line-height: 1.6; margin: 0 0 25px;">
                            我们收到了您的密码重置请求。请点击下面的按钮来重置您的密码：
                        </p>

                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #28a745 0%, #34ce57 100%); color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);">
                                重置我的密码
                            </a>
                        </div>

                        <!-- Warning Box -->
                        <div style="background: #fff8e6; border: 1px solid #ffe08a; border-radius: 10px; padding: 20px; margin: 25px 0;">
                            <p style="color: #856404; font-weight: 600; margin: 0 0 10px; font-size: 14px;">
                                ⚠️ 安全提示
                            </p>
                            <ul style="color: #856404; font-size: 14px; margin: 0; padding-left: 20px; line-height: 1.8;">
                                <li>此链接将在 <strong>1小时</strong> 后失效</li>
                                <li>如果您没有请求重置密码，请忽略此邮件</li>
                                <li>请勿将此链接分享给他人</li>
                            </ul>
                        </div>

                        <p style="color: #666; font-size: 14px; margin: 20px 0 10px;">如果按钮无法点击，请复制以下链接到浏览器中访问：</p>
                        <p style="word-break: break-all; background: #f8f9fa; padding: 12px 15px; border-radius: 8px; font-size: 12px; color: #28a745; border: 1px solid #e9ecef; margin: 0;">
                            {reset_url}
                        </p>
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background-color: #f8f9fa; padding: 25px 30px; text-align: center; border: 1px solid #e9ecef; border-top: none; border-radius: 0 0 10px 10px;">
                        <p style="color: #999; font-size: 12px; margin: 0 0 8px;">此邮件由系统自动发送，请勿直接回复。</p>
                        <p style="color: #999; font-size: 12px; margin: 0;">© 2025 悦行假期 Joyeful Escapes. All rights reserved.</p>
                    </td>
                </tr>
            </table>
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

© 2025 悦行假期 Joyeful Escapes. All rights reserved.
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

        # 从Flask配置中获取发件人信息
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME', 'noreply@joyesc.com')
        sender_str = f"悦行假期 Joyeful Escapes <{sender_email}>"

        subject = '【悦行假期】邮箱验证码'

        # HTML邮件内容 - 绿色会员风格
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <tr>
                    <td style="background: linear-gradient(135deg, #28a745 0%, #34ce57 100%); padding: 40px 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <div style="width: 70px; height: 70px; background: rgba(255,255,255,0.2); border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                            <span style="font-size: 32px;">📧</span>
                        </div>
                        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">邮箱验证</h1>
                        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0; font-size: 14px;">悦行假期 Joyeful Escapes</p>
                    </td>
                </tr>

                <!-- Content -->
                <tr>
                    <td style="padding: 40px 30px; background-color: #ffffff; border-left: 1px solid #e9ecef; border-right: 1px solid #e9ecef;">
                        <p style="color: #333; font-size: 16px; margin: 0 0 20px;">尊敬的 <strong>{username}</strong>，您好！</p>

                        <p style="color: #666; font-size: 15px; line-height: 1.6; margin: 0 0 25px;">
                            您的邮箱验证码是：
                        </p>

                        <!-- Verification Code Box -->
                        <div style="text-align: center; margin: 30px 0;">
                            <div style="display: inline-block; background: linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(52, 206, 87, 0.1) 100%); border: 2px dashed #28a745; border-radius: 12px; padding: 20px 40px;">
                                <span style="font-size: 36px; font-weight: bold; color: #28a745; letter-spacing: 10px;">{verification_code}</span>
                            </div>
                        </div>

                        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 15px 20px; margin: 25px 0; text-align: center;">
                            <p style="color: #166534; font-size: 14px; margin: 0;">
                                ⏱️ 验证码有效期为 <strong>10分钟</strong>，请尽快使用
                            </p>
                        </div>

                        <p style="color: #999; font-size: 14px; margin: 20px 0 0; text-align: center;">
                            如果您没有请求此验证码，请忽略此邮件。
                        </p>
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background-color: #f8f9fa; padding: 25px 30px; text-align: center; border: 1px solid #e9ecef; border-top: none; border-radius: 0 0 10px 10px;">
                        <p style="color: #999; font-size: 12px; margin: 0 0 8px;">此邮件由系统自动发送，请勿直接回复。</p>
                        <p style="color: #999; font-size: 12px; margin: 0;">© 2025 悦行假期 Joyeful Escapes. All rights reserved.</p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        '''

        text_body = f'''
尊敬的 {username}，您好！

您的邮箱验证码是：{verification_code}

验证码有效期为10分钟，请尽快使用。

如果您没有请求此验证码，请忽略此邮件。

此邮件由系统自动发送，请勿直接回复。

© 2025 悦行假期 Joyeful Escapes. All rights reserved.
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

