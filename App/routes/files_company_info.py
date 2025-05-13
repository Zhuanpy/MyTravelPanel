from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from ..models.Packagemodels import db, CompanyInfo
from datetime import datetime
import os

# 创建蓝图
company_info = Blueprint('company_info', __name__)

def normalize_path(path):
    """统一路径格式，将反斜杠转换为正斜杠"""
    return path.replace('\\', '/')

@company_info.route('/company/edit', methods=['GET', 'POST'])
def edit_company_info():
    company = CompanyInfo.query.first()
    
    if request.method == 'POST':
        try:
            if company is None:
                company = CompanyInfo()
            
            company.company_name = request.form['company_name']
            company.company_description = request.form['company_description']
            company.phone = request.form['phone']
            company.email = request.form['email']
            company.address = request.form['address']
            
            # 处理logo上传
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo.filename != '':
                    # 确保文件名安全
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(logo.filename)
                    # 构建相对路径（不包含static前缀）
                    logo_path = 'images/' + filename
                    # 构建完整的文件系统路径用于保存文件
                    full_path = os.path.join(os.getcwd(), 'static', 'images', filename)
                    # 确保目录存在
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    # 保存文件
                    logo.save(full_path)
                    # 保存相对路径到数据库
                    company.logo_path = logo_path
            
            if company.id is None:
                db.session.add(company)
            
            db.session.commit()
            
            flash('公司信息更新成功！', 'success')
            return redirect(url_for('company_info.edit_company_info'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    # 如果是现有记录，确保显示时路径格式正确
    if company and company.logo_path:
        company.logo_path = normalize_path(company.logo_path)
    
    return render_template('company/edit_company_info.html', company=company)

@company_info.route('/company/info')
def get_company_info():
    company = CompanyInfo.query.first()
    if company:
        # 确保返回的JSON中路径格式正确
        company_data = {
            'company_name': company.company_name,
            'company_description': company.company_description,
            'phone': company.phone,
            'email': company.email,
            'address': company.address,
            'logo_path': normalize_path(company.logo_path) if company.logo_path else None
        }
        return jsonify(company_data)
    return jsonify({}), 404


@company_info.route('/company_header')
def company_header():
    company = CompanyInfo.query.first()
    if company and company.logo_path:
        company.logo_path = normalize_path(company.logo_path)
    return render_template('company/company_header.html', company=company)