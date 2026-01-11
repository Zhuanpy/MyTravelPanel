# -*- coding: utf-8 -*-
"""
供应商路由 - 已合并到公司管理
此文件保留用于向后兼容，所有供应商路由重定向到 corporate 蓝图
"""

from flask import Blueprint, render_template, request, redirect, url_for
from App_new.exts import db
from App_new.business.projects.models.project import CustomerCompany

# 创建蓝图
supplier = Blueprint('finance_supplier', __name__)


@supplier.route('/')
def suppliers():
    """供应商列表 -> 重定向到公司列表（供应商筛选）"""
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/supplier/<int:supplier_id>', methods=['GET'])
def view_supplier(supplier_id):
    """查看供应商 -> 重定向到公司详情"""
    company = CustomerCompany.query.filter(
        CustomerCompany.id == supplier_id,
        CustomerCompany.is_supplier == True
    ).first()
    if company:
        return redirect(url_for('corporate.company_detail', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/add', methods=['GET', 'POST'])
def add_supplier():
    """添加供应商 -> 重定向到公司创建页面"""
    return redirect(url_for('corporate.create_company'))


@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    """编辑供应商 -> 重定向到公司编辑页面"""
    company = CustomerCompany.query.filter(
        CustomerCompany.id == supplier_id,
        CustomerCompany.is_supplier == True
    ).first()
    if company:
        return redirect(url_for('corporate.edit_company', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/delete/<int:supplier_id>')
def delete_supplier(supplier_id):
    """删除供应商 -> 重定向到公司删除"""
    company = CustomerCompany.query.filter(
        CustomerCompany.id == supplier_id,
        CustomerCompany.is_supplier == True
    ).first()
    if company:
        return redirect(url_for('corporate.delete_company', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))
