# -*- coding: utf-8 -*-
"""
域名配置工具
用于管理网站域名相关的配置
"""

from flask import current_app, request
from urllib.parse import urljoin, urlparse

def get_domain():
    """获取当前域名"""
    if current_app.config.get('DOMAIN'):
        return current_app.config['DOMAIN']
    
    # 如果没有配置，从请求中获取
    if request:
        return request.host
    return 'localhost'

def get_base_url():
    """获取基础URL"""
    if current_app.config.get('BASE_URL'):
        return current_app.config['BASE_URL']
    
    # 如果没有配置，从请求中构建
    if request:
        scheme = 'https' if request.is_secure else 'http'
        return f"{scheme}://{request.host}"
    return 'http://localhost:5000'

def build_url(path=''):
    """构建完整的URL"""
    base_url = get_base_url()
    if path.startswith('http'):
        return path
    return urljoin(base_url, path.lstrip('/'))

def is_production():
    """检查是否为生产环境"""
    return current_app.config.get('FLASK_ENV') == 'production'

def get_site_name():
    """获取网站名称"""
    return current_app.config.get('SITE_NAME', 'JoyEsc Travel Panel')

def get_site_description():
    """获取网站描述"""
    return current_app.config.get('SITE_DESCRIPTION', '专业的旅游服务管理平台')

def get_contact_email():
    """获取联系邮箱"""
    return current_app.config.get('CONTACT_EMAIL', 'contact@joyesc.com')

def get_support_phone():
    """获取客服电话"""
    return current_app.config.get('SUPPORT_PHONE', '+65 1234 5678')

def get_social_links():
    """获取社交媒体链接"""
    return {
        'facebook': current_app.config.get('FACEBOOK_URL', 'https://facebook.com/joyesc'),
        'instagram': current_app.config.get('INSTAGRAM_URL', 'https://instagram.com/joyesc'),
        'twitter': current_app.config.get('TWITTER_URL', 'https://twitter.com/joyesc'),
        'linkedin': current_app.config.get('LINKEDIN_URL', 'https://linkedin.com/company/joyesc')
    }

def get_legal_info():
    """获取法律信息"""
    return {
        'company_name': current_app.config.get('COMPANY_NAME', 'JoyEsc Pte Ltd'),
        'company_address': current_app.config.get('COMPANY_ADDRESS', 'Singapore'),
        'privacy_policy_url': build_url('/privacy-policy'),
        'terms_of_service_url': build_url('/terms-of-service'),
        'cookie_policy_url': build_url('/cookie-policy')
    }

def get_analytics_config():
    """获取分析配置"""
    return {
        'google_analytics_id': current_app.config.get('GOOGLE_ANALYTICS_ID'),
        'facebook_pixel_id': current_app.config.get('FACEBOOK_PIXEL_ID'),
        'hotjar_id': current_app.config.get('HOTJAR_ID')
    }

def get_payment_config():
    """获取支付配置"""
    return {
        'stripe_public_key': current_app.config.get('STRIPE_PUBLIC_KEY'),
        'paypal_client_id': current_app.config.get('PAYPAL_CLIENT_ID'),
        'supported_currencies': current_app.config.get('SUPPORTED_CURRENCIES', ['SGD', 'USD', 'EUR'])
    }

def get_email_config():
    """获取邮件配置"""
    return {
        'noreply_email': current_app.config.get('NOREPLY_EMAIL', 'noreply@joyesc.com'),
        'support_email': current_app.config.get('SUPPORT_EMAIL', 'support@joyesc.com'),
        'marketing_email': current_app.config.get('MARKETING_EMAIL', 'marketing@joyesc.com')
    }
