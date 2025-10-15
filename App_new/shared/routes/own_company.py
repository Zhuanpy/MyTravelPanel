from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from App_new.exts import db
from App_new.business.tour.models.Packagemodels import CompanyInfo
import os

# 创建蓝图
own_company = Blueprint('own_company', __name__)

def normalize_path(path):
    """统一路径格式，将反斜杠转换为正斜杠"""
    return path.replace('\\', '/')

@own_company.route('/company_info')
def company_info_page():
    """公司信息页面路由"""
    return render_template('utils/公司信息.html')

@own_company.route('/api/company_info', methods=['GET'])
def get_company_info():
    """获取公司信息API"""
    company = CompanyInfo.query.first()
    if company:
        return jsonify({
            'id': company.id,
            'name': company.name,
            'address': company.address,
            'phone': company.phone,
            'email': company.email,
            'website': company.website,
            'description': company.description
        })
    return jsonify({}), 404

@own_company.route('/api/company_info', methods=['POST'])
def create_company_info():
    """创建公司信息API"""
    data = request.get_json()
    company = CompanyInfo(
        name=data['name'],
        address=data.get('address'),
        phone=data.get('phone'),
        email=data.get('email'),
        website=data.get('website'),
        description=data.get('description')
    )
    db.session.add(company)
    db.session.commit()
    return jsonify({
        'id': company.id,
        'name': company.name,
        'address': company.address,
        'phone': company.phone,
        'email': company.email,
        'website': company.website,
        'description': company.description
    })

@own_company.route('/api/company_info/<int:company_id>', methods=['PUT'])
def update_company_info(company_id):
    """更新公司信息API"""
    company = CompanyInfo.query.get_or_404(company_id)
    data = request.get_json()
    
    company.name = data.get('name', company.name)
    company.address = data.get('address', company.address)
    company.phone = data.get('phone', company.phone)
    company.email = data.get('email', company.email)
    company.website = data.get('website', company.website)
    company.description = data.get('description', company.description)
    
    db.session.commit()
    return jsonify({
        'id': company.id,
        'name': company.name,
        'address': company.address,
        'phone': company.phone,
        'email': company.email,
        'website': company.website,
        'description': company.description
    })

@own_company.route('/company/edit', methods=['GET', 'POST'])
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
            return redirect(url_for('own_company.edit_company_info'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    # 如果是现有记录，确保显示时路径格式正确
    if company and company.logo_path:
        company.logo_path = normalize_path(company.logo_path)
    
    return render_template('shared/own_company/own_company_form.html', company=company)

@own_company.route('/company_header')
def company_header():
    company = CompanyInfo.query.first()
    if company and company.logo_path:
        company.logo_path = normalize_path(company.logo_path)
    return render_template('shared/own_company/own_company_header.html', company=company)