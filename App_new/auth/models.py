# -*- coding: utf-8 -*-
"""认证相关数据模型 - 重新导出真正的模型"""

from .models.auth import AuthUser, Role, UserProfile

# 导出所有模型供其他模块使用
__all__ = ['AuthUser', 'Role', 'UserProfile']
