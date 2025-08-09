import os
import logging
from dotenv import load_dotenv
from pathlib import Path
import numpy as np

# 加载 .env 文件中的环境变量
load_dotenv()


class Config:
    # 数据库配置 - 优先使用环境变量，开发环境提供默认值
    DB_USER = os.getenv('DB_USER', 'your_db_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_db_password')  # 生产环境必须使用环境变量
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    # 新增：可单独指定端口（若 DB_HOST 已含端口，将优先生效）
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    DB_NAME = os.getenv('DB_NAME', 'your_database_name')
    DB_NAME_DATA = os.getenv('DB_NAME_DATA', 'your_data_database_name')

    # 资源文件夹路径配置
    # 获取项目根目录（与App文件夹同级）
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    # 资源文件夹路径（现在与App文件夹同级）
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

    # 在生产环境验证必需的环境变量
    @classmethod
    def validate_config(cls):
        """验证配置，生产环境下检查敏感信息"""
        env = os.getenv('FLASK_ENV', 'development')
        if env == 'production':
            required_vars = ['DB_USER', 'DB_PASSWORD', 'SECRET_KEY', 'MAIL_USERNAME', 'MAIL_PASSWORD']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables for production: {', '.join(missing_vars)}")

    # 构建数据库 URI（兼容 DB_HOST 已包含端口；否则使用 DB_PORT）
    _HOST_WITH_PORT = DB_HOST if (':' in str(DB_HOST)) else f"{DB_HOST}:{DB_PORT}"
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{_HOST_WITH_PORT}/{DB_NAME}'
    SQLALCHEMY_DATABASE_URI_DATA = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{_HOST_WITH_PORT}/{DB_NAME_DATA}'

    # SQLAlchemy 配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 关闭 SQL 日志输出

    # Flask-Caching 配置
    CACHE_TYPE = 'SimpleCache'  # 使用简单的内存缓存
    CACHE_DEFAULT_TIMEOUT = 300  # 缓存默认过期时间（秒）

    # 日志配置
    LOG_LEVEL = logging.INFO
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo': False,  # 关闭 SQL 语句输出
        'echo_pool': False,  # 关闭连接池日志
        'pool_pre_ping': True,  # 启用连接池健康检查
        'pool_recycle': 3600,  # 连接回收时间（秒）
    }

    # Flask 安全配置 - 优先使用环境变量
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

    # 邮件服务器配置 - 优先使用环境变量
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'your_email@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'your_email_password')

    # 邮件发送配置
    MAIL_CONFIG = {
        'DEFAULT_SENDER': {
            'name': '待办事项提醒系统',
            'email': 'your_email@gmail.com',
        },
        'DEFAULT_RECIPIENTS': [
            # 默认收件人列表
            {'name': '主要收件人', 'email': 'recipient@example.com'},
        ],
        'CC_LIST': ['cc@example.com'],  # 抄送列表
        'BCC_LIST': [],  # 密送列表
    }

    # 待办事项通知配置
    TODO_NOTIFICATION = {
        'ENABLED': os.getenv('TODO_NOTIFICATION_ENABLED', 'True').lower() in ('true', '1', 't'),
        'CHECK_INTERVAL': int(os.getenv('TODO_CHECK_INTERVAL', 6 * 60 * 60)),  # 默认6小时
        'EMAIL_INTERVAL': int(os.getenv('TODO_EMAIL_INTERVAL', 12 * 60 * 60)),  # 默认12小时
        'EMAIL_THRESHOLD': int(os.getenv('TODO_EMAIL_THRESHOLD', 24)),  # 默认24小时
        'DESKTOP_NOTIFICATION': os.getenv('TODO_DESKTOP_NOTIFICATION', 'True').lower() in ('true', '1', 't'),
    }

    # Redis 配置（如果使用）
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # 第三方服务 API 密钥
    API_KEYS = {
        'google_maps': os.getenv('GOOGLE_MAPS_API_KEY'),
        'weather': os.getenv('WEATHER_API_KEY'),
        'payment_gateway': os.getenv('PAYMENT_GATEWAY_API_KEY'),
    }

    # 报表表头配置
    REPORT_HEADERS = {
        # 标准订单报表表头（16个字段）
        'order_report': [
            'order_id',  # 1. 订单ID
            'customer_type',  # 2. 客户类型
            'order_date',  # 3. 订单日期
            'passenger_name',  # 4. 乘客姓名
            'travel_date',  # 5. 旅行日期
            'product_name',  # 6. 产品名称
            'booking_type',  # 7. 预订类型
            'selling_price',  # 8. 销售价格
            'cost_price',  # 9. 成本价格
            'profit',  # 10. 利润
            'profit_margin',  # 11. 利润率
            'balance',  # 12. 余额
            'created_by',  # 13. 创建人
            'approved_by',  # 14. 审批人
            'pax_info',  # 15. 乘客信息
            'invoice_status'  # 16. 发票状态
        ],

        # 简化的订单报表表头（常用字段）
        'simple_order_report': [
            'order_id',
            'customer_type',
            'order_date',
            'passenger_name',
            'product_name',
            'selling_price',
            'cost_price',
            'profit',
            'created_by'
        ],

        # 财务报表表头
        'financial_report': [
            'date',
            'description',
            'amount',
            'type',
            'category',
            'reference'
        ],

        # 发票数据表头（根据read_all_inv方法中的列处理逻辑）
        'invoice_data': [
            'hid',  # 0. HID编号
            'customer_name',  # 2. 客户姓名
            'order_date',  # 3. 订单日期
            'product_name',  # 4. 产品名称
            'travel_date',  # 5. 旅行日期
            'selling_price',  # 6. 销售价格
            'cost_price',  # 8. 成本价格
            'profit',  # 11. 利润
            'balance',  # 12. 余额
            'created_by',  # 13. 创建人
            'approved_by'  # 14. 审批人
        ],

        # HID数据表头（根据read_all_hid方法中的列处理逻辑）
        'hid_data': [
            'hid',  # 0. HID编号
            'customer_name',  # 2. 客户姓名
            'order_date',  # 3. 订单日期
            'travel_date',  # 4. 旅行日期
            'product_name',  # 5. 产品名称
            'booking_type',  # 7. 预订类型
            'selling_price',  # 8. 销售价格
            'cost_price',  # 9. 成本价格
            'profit',  # 10. 利润
            'created_by'  # 11. 创建人
        ]
    }

    # 获取表头字符串（用逗号分隔）
    @classmethod
    def get_header_string(cls, header_type='order_report'):
        """获取指定类型的表头字符串"""
        if header_type in cls.REPORT_HEADERS:
            return ','.join(cls.REPORT_HEADERS[header_type])
        else:
            raise ValueError(f"未知的表头类型: {header_type}")

    # 获取表头列表
    @classmethod
    def get_header_list(cls, header_type='order_report'):
        """获取指定类型的表头列表"""
        if header_type in cls.REPORT_HEADERS:
            return cls.REPORT_HEADERS[header_type].copy()
        else:
            raise ValueError(f"未知的表头类型: {header_type}")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True  # 开发环境下开启 SQL 日志
    LOG_LEVEL = logging.DEBUG  # 开发环境下使用更详细的日志级别


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False  # 生产环境下关闭 SQL 日志
    LOG_LEVEL = logging.WARNING  # 生产环境下只显示警告和错误


# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


# 获取当前环境的配置
def get_config():
    env = os.getenv('FLASK_ENV', 'default')
    return config[env]


def safe_json(data):
    if isinstance(data, list):
        return [safe_json(item) for item in data]
    elif isinstance(data, dict):
        return {k: safe_json(v) for k, v in data.items()}
    elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    else:
        return data 