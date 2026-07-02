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
    VisaTemplateFiles,  # 修正：实际类名是 VisaTemplateFiles
    VisaFormCoordinate,  # 签证表单填写坐标表（原坐标列表.xls）
    VisaProjectFormData,  # 签证项目填表数据表（替代手工编辑 FormSample.xls 的值）
    VisaFormTemplate  # 签证填表模板（可套用到新项目）
)

__all__ = [
    'VisaCountries',
    'VisaTypes',
    'VisaDocuments',
    'VisaProject',  # 修正导出名称
    # 'VisaProjectDocuments',  # 暂时注释掉，因为类不存在
    'VisaLinks',  # 修正：实际类名是 VisaLinks
    'VisaTemplateFiles',  # 修正：实际类名是 VisaTemplateFiles
    'VisaFormCoordinate',  # 签证表单填写坐标表
    'VisaProjectFormData',  # 签证项目填表数据表
    'VisaFormTemplate'  # 签证填表模板
]
