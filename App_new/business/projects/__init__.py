# -*- coding: utf-8 -*-
"""
项目管理业务模块
包含项目的创建、查看、编辑、删除等所有项目管理功能
"""

from flask import Blueprint

# 创建项目管理蓝图（保持历史端点前缀 business_projects）
projects_bp = Blueprint('business_projects', __name__, url_prefix='/projects')

# 导入路由
from .routes import project_list, project_detail, project_create, project_edit, project_header, project_ref, project_eo, project_receipt, project_invoice, project_members, project_home, project_settlement, project_prepayment, project_payment

# 注册路由
projects_bp.register_blueprint(project_home.project_home)  # 首页，无前缀
projects_bp.register_blueprint(project_list.bp, url_prefix='/list')
projects_bp.register_blueprint(project_detail.bp, url_prefix='/detail')
projects_bp.register_blueprint(project_create.project_create, url_prefix='/create')
projects_bp.register_blueprint(project_edit.bp, url_prefix='/edit')
projects_bp.register_blueprint(project_header.project_header, url_prefix='/header')
projects_bp.register_blueprint(project_ref.project_ref, url_prefix='/ref')
projects_bp.register_blueprint(project_eo.project_eo, url_prefix='/eo')
projects_bp.register_blueprint(project_receipt.project_receipt, url_prefix='/receipt')
projects_bp.register_blueprint(project_invoice.project_invoice, url_prefix='/invoice')
projects_bp.register_blueprint(project_members.project_members_bp)
projects_bp.register_blueprint(project_settlement.bp, url_prefix='/settlement')
projects_bp.register_blueprint(project_prepayment.project_prepayment)  # 预付账款，已包含 url_prefix='/prepayment'
projects_bp.register_blueprint(project_payment.project_payment)  # 付款记录，已包含 url_prefix='/payment'

__all__ = ['projects_bp']
