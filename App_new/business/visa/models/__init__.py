# -*- coding: utf-8 -*-
"""
签证相关数据模型包
"""

from .Visamodels import (
    VisaCountries,
    VisaTypes,
    VisaDocuments,
    VisaProject,  # 修正：实际定义为 VisaProject（单数）
    VisaProjectDocuments,
    VisaProjectLinks,
    VisaProjectFiles
)

__all__ = [
    'VisaCountries',
    'VisaTypes', 
    'VisaDocuments',
    'VisaProject',  # 修正导出名称
    'VisaProjectDocuments',
    'VisaProjectLinks',
    'VisaProjectFiles'
]
