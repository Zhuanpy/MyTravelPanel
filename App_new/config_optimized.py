# -*- coding: utf-8 -*-
"""
优化后的配置文件
分离敏感信息和非敏感配置
"""

import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件中的环境变量
load_dotenv()

class Config:
    """基础配置类 - 只包含非敏感配置"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 域名配置
    DOMAIN = os.environ.get('DOMAIN', 'joyesc.com')
    BASE_URL = os.environ.get('BASE_URL', 'https://joyesc.com')
    
    # 数据库配置 - 从环境变量读取
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '***REMOVED****')
    DB_HOST = os.environ.get('DB_HOST', '47.84.177.3')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'travelindustry')
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # SQLAlchemy 连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo': False,
        'echo_pool': False,
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 20,
        'pool_size': 10,
        'max_overflow': 20,
    }
    
    # Flask配置
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    TESTING = False
    SKIP_DB_INIT = os.environ.get('SKIP_DB_INIT', 'false').lower() == 'true'
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV', 'development') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    
    # 资源文件夹路径配置
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RESOURCES_ROOT = PROJECT_ROOT / "资源"
    
    # 业务路径配置
    VISA_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "Visa"
    VISA_RESOURCES_PATH = RESOURCES_ROOT / "签证"
    TOUR_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "Tour"
    TOUR_RESOURCES_PATH = RESOURCES_ROOT / "旅游产品"
    FLIGHT_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "机票"
    FLIGHT_RESOURCES_PATH = RESOURCES_ROOT / "机票产品"
    FLIGHT_REFUND_PATH = FLIGHT_PROJECTS_PATH / "退票"
    CUSTOMER_DATA_PATH = RESOURCES_ROOT / "客户资料"
    BILLING_DATA_PATH = RESOURCES_ROOT / "账单"
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # 邮件配置 - 从环境变量读取敏感信息
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # 默认收件人邮箱（当无法获取经办人邮箱时使用）
    DEFAULT_EMAIL_RECIPIENT = os.environ.get('DEFAULT_EMAIL_RECIPIENT', 'admin@joyesc.com')
    
    # 多个默认收件人邮箱（用逗号分隔，优先级高于单个默认收件人）
    DEFAULT_EMAIL_RECIPIENTS = os.environ.get('DEFAULT_EMAIL_RECIPIENTS', '')
    
    # 第三方服务配置
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
    PAYMENT_GATEWAY_API_KEY = os.environ.get('PAYMENT_GATEWAY_API_KEY')
    
    # Redis 配置
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # 待办事项通知配置
    TODO_NOTIFICATION_ENABLED = os.environ.get('TODO_NOTIFICATION_ENABLED', 'True').lower() == 'true'
    TODO_CHECK_INTERVAL = int(os.environ.get('TODO_CHECK_INTERVAL', 21600))
    TODO_EMAIL_INTERVAL = int(os.environ.get('TODO_EMAIL_INTERVAL', 43200))
    TODO_EMAIL_THRESHOLD = int(os.environ.get('TODO_EMAIL_THRESHOLD', 24))
    TODO_DESKTOP_NOTIFICATION = os.environ.get('TODO_DESKTOP_NOTIFICATION', 'True').lower() == 'true'
    
    @staticmethod
    def validate_config():
        """验证配置"""
        # 检查必需的环境变量
        required_env_vars = [
            'SECRET_KEY',
            'DB_PASSWORD',
            'MAIL_USERNAME',
            'MAIL_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
            print("请在 .env 文件中设置这些变量")
            return False
        
        # 检查必需目录
        required_dirs = ['logs', 'uploads']
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                print(f"✅ 创建目录: {dir_name}")
        
        print("✅ 配置验证完成")
        return True
    
    @staticmethod
    def get_mail_config():
        """获取邮件配置信息（用于测试）"""
        return {
            'MAIL_SERVER': Config.MAIL_SERVER,
            'MAIL_PORT': Config.MAIL_PORT,
            'MAIL_USERNAME': Config.MAIL_USERNAME,
            'MAIL_PASSWORD': '已设置' if Config.MAIL_PASSWORD else '未设置'
        }


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
