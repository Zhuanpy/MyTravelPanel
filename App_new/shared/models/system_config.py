"""
系统配置模型 - key/value 全局配置
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ...exts import db


class SystemConfig(db.Model):
    """系统全局配置（key-value）"""
    __tablename__ = 'system_config'

    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, default='')
    description = Column(String(200), default='')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemConfig {self.config_key}>'

    @classmethod
    def get(cls, key, default=None):
        """获取配置值"""
        item = cls.query.filter_by(config_key=key).first()
        return item.config_value if item and item.config_value else default

    @classmethod
    def set(cls, key, value, description=''):
        """设置配置值"""
        item = cls.query.filter_by(config_key=key).first()
        if item:
            item.config_value = value
            if description:
                item.description = description
            item.updated_at = datetime.utcnow()
        else:
            item = cls(config_key=key, config_value=value, description=description)
            db.session.add(item)
        return item

    @classmethod
    def get_payment_config(cls):
        """获取付款配置"""
        keys = ['payment_bank_name', 'payment_account_name',
                'payment_account_number', 'payment_qr_image', 'payment_note']
        return {k: cls.get(k, '') for k in keys}
