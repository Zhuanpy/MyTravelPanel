# -*- coding: utf-8 -*-
"""
新架构配置文件
基于原有配置的简化版本，用于新架构启动
"""

import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件中的环境变量
load_dotenv()

class Config:
    """基础配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 域名配置
    DOMAIN = os.environ.get('DOMAIN', 'joyesc.com')
    BASE_URL = os.environ.get('BASE_URL', 'https://joyesc.com')
    
    # 数据库配置 - 从环境变量读取，请在 .env 中配置（生产必须显式设置 DB_PASSWORD）
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'travelindustry')

    if not DB_PASSWORD:
        # 启动时无密码 -> 仅打印警告，让 SQLAlchemy 自然抛连接错误。
        # 不直接 raise 是为了允许 sqlite 测试环境与本地 root 无密 MySQL 等情况。
        print("⚠️  DB_PASSWORD 未设置，请检查 .env 文件（或 systemd EnvironmentFile）")

    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # SQLAlchemy 连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo': False,  # 关闭 SQL 语句输出
        'echo_pool': False,  # 关闭连接池日志
        'pool_pre_ping': True,  # 启用连接池健康检查
        'pool_recycle': 3600,  # 连接回收时间（秒）
        'pool_timeout': 20,  # 获取连接的超时时间（秒）
        'pool_size': 10,  # 连接池大小
        'max_overflow': 20,  # 最大溢出连接数
    }
    
    # Flask配置
    DEBUG = True
    TESTING = False
    SKIP_DB_INIT = os.environ.get('SKIP_DB_INIT', 'false').lower() == 'true'
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # 开发环境设为False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

    # 性能监控（用于排查 CPU 飙高的根因）
    # 日志输出到 logs/slow_request.log 和 logs/slow_query.log
    MONITORING_ENABLED = os.environ.get('MONITORING_ENABLED', 'true').lower() == 'true'
    SLOW_REQUEST_THRESHOLD_MS = int(os.environ.get('SLOW_REQUEST_THRESHOLD_MS', 1000))
    SLOW_QUERY_THRESHOLD_MS = int(os.environ.get('SLOW_QUERY_THRESHOLD_MS', 500))
    
    # 资源文件夹路径配置
    # 获取项目根目录（与App_new文件夹同级）
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    
    # 资源文件夹路径（现在与App_new文件夹同级）
    RESOURCES_ROOT = PROJECT_ROOT / "资源"
    
    # 签证相关路径
    VISA_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "Visa"  # 签证项目文件夹
    VISA_RESOURCES_PATH = RESOURCES_ROOT / "签证"  # 签证资源文件夹
    
    # 旅游相关路径
    TOUR_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "Tour"  # 旅游项目文件夹
    TOUR_RESOURCES_PATH = RESOURCES_ROOT / "旅游产品"  # 旅游资源文件夹
    
    # 机票相关路径
    FLIGHT_PROJECTS_PATH = RESOURCES_ROOT / "Project" / "机票"  # 机票项目文件夹
    FLIGHT_RESOURCES_PATH = RESOURCES_ROOT / "机票产品"  # 机票资源文件夹
    FLIGHT_REFUND_PATH = FLIGHT_PROJECTS_PATH / "退票"  # 退票文件夹
    
    # 客户资料路径
    CUSTOMER_DATA_PATH = RESOURCES_ROOT / "客户资料"  # 客户资料文件夹
    
    # 账单路径
    BILLING_DATA_PATH = RESOURCES_ROOT / "账单"  # 账单文件夹
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # 报表表头配置
    REPORT_HEADERS = {
        # 订单报表表头（16个字段）
        'order_report': [
            'hid', 'company_name', 'booking_date', 'passenger_name',
            'departure_date', 'itinerary', 'currency', 'selling_price',
            'cost_price', 'profit', 'profit_margin', 'balance',
            'employee_name', 'salesperson_name', 'pax_count', 'remarks'
        ],
        
        # 发票数据表头（29个字段）
        'invoice_data': [
            'hid', 'company_name', 'inv', 'inv_date', 'client_name',
            'departure_date', 'itinerary', 'currency', 'gross', 'commission',
            'discount', 'selling_price', 'cost_price', 'profit', 'profit_margin',
            'balance', 'invoice_person', 'contact_person', 'salesperson', 'remarks',
            'itinerary_date', 'pax_count', 'sales_account', 'invoice_account',
            'invoice_profit', 'remarks_1', 'remarks_2', 'hid_date', 'remarks_3'
        ],
        
        # 简化订单报表表头（9个字段）
        'simple_order_report': [
            'hid', 'company_name', 'booking_date', 'passenger_name',
            'selling_price', 'cost_price', 'profit', 'employee_name', 'remarks'
        ],
        
        # 财务报表表头（6个字段）
        'financial_report': [
            'hid', 'company_name', 'selling_price', 'cost_price',
            'profit', 'booking_date'
        ],
    }
    
    # 邮件配置 - 阿里云企业邮箱
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.qiye.aliyun.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'info@joyesc.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'info@joyesc.com')
    # 邮件收件人配置（从环境变量加载，供提醒功能使用）
    # 当 DEFAULT_EMAIL_RECIPIENTS 存在时优先使用，多邮箱用英文逗号分隔
    DEFAULT_EMAIL_RECIPIENT = os.environ.get('DEFAULT_EMAIL_RECIPIENT')
    DEFAULT_EMAIL_RECIPIENTS = os.environ.get('DEFAULT_EMAIL_RECIPIENTS', '')
    
    @staticmethod
    def get_header_list(header_type='order_report'):
        """
        获取指定类型的报表表头列表
        
        Args:
            header_type (str): 表头类型
        
        Returns:
            list: 表头列表
        """
        return Config.REPORT_HEADERS.get(header_type, Config.REPORT_HEADERS['order_report'])
    
    @staticmethod
    def get_header_string(header_type='order_report'):
        """
        获取指定类型的报表表头字符串（用逗号分隔）
        
        Args:
            header_type (str): 表头类型
        
        Returns:
            str: 表头字符串
        """
        headers = Config.get_header_list(header_type)
        return ','.join(headers)
    
    @staticmethod
    def validate_config():
        """验证配置"""
        required_dirs = [
            'logs',
            'uploads',
        ]
        
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                print(f"✅ 创建目录: {dir_name}")
        
        print("✅ 配置验证完成")
        return True
    
    @staticmethod
    def safe_json(data):
        """安全地转换数据为JSON格式，处理NaN和Inf值"""
        import numpy as np
        
        if isinstance(data, list):
            return [Config.safe_json(item) for item in data]
        elif isinstance(data, dict):
            return {k: Config.safe_json(v) for k, v in data.items()}
        elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
            return None
        else:
            return data


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