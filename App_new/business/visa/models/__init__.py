# -*- coding: utf-8 -*-
"""
签证相关数据模型包
"""

from .Visamodels import (
    VisaCountries,
    VisaTypes,
    VisaDocuments,
    VisaProject,  # 修正：实际定义为 VisaProject（单数）
    # VisaProjectDocuments,  # 暂时注释掉，因为类不存在
    VisaLinks,  # 修正：实际类名是 VisaLinks
    VisaTemplateFiles  # 修正：实际类名是 VisaTemplateFiles
)

__all__ = [
    'VisaCountries',
    'VisaTypes', 
    'VisaDocuments',
    'VisaProject',  # 修正导出名称
    # 'VisaProjectDocuments',  # 暂时注释掉，因为类不存在
    'VisaLinks',  # 修正：实际类名是 VisaLinks
    'VisaTemplateFiles'  # 修正：实际类名是 VisaTemplateFiles
]
