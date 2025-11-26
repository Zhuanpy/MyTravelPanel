from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from App_new.exts import db, csrf
from App_new.business.tour.models.Packagemodels import CompanyInfo
import os

# 创建蓝图
own_company = Blueprint('own_company', __name__)

def normalize_path(path):
    """统一路径格式，将反斜杠转换为正斜杠"""
    return path.replace('\\', '/')

def get_company_info():
    """获取公司信息（用于模板）"""
    try:
        company = CompanyInfo.query.first()
        if company and company.logo_path:
            # 标准化路径并移除多余的前缀
            path = normalize_path(company.logo_path)
            # 移除可能存在的 'static/' 或 'App_new/static/' 前缀
            path = path.replace('App_new/static/', '')
            path = path.replace('static/', '')
            # 如果路径不包含 'company/' 前缀，且不是绝对路径，则添加 'company/' 前缀
            if not path.startswith('company/') and not os.path.isabs(path):
                # 检查是否是文件名（不包含路径分隔符）
                if '/' not in path and '\\' not in path:
                    path = os.path.join('company', path).replace('\\', '/')
            company.logo_path = path
        return company
    except Exception as e:
        # 如果查询失败，返回None而不是抛出异常
        print(f"获取公司信息失败: {str(e)}")
        return None

# 注册context processor，让模板可以访问公司信息
@own_company.app_context_processor
def inject_company_info():
    return dict(get_company_info=get_company_info)

@own_company.route('/company_info')
def company_info_page():
    """公司信息页面路由"""
    return render_template('utils/公司信息.html')

@own_company.route('/api/company_info', methods=['GET'])
def get_company_info_api():
    """获取公司信息API"""
    company = CompanyInfo.query.first()
    if company:
        return jsonify({
            'id': company.id,
            'company_name': company.company_name,
            'company_name_cn': company.company_name_cn,
            'company_short_name': company.company_short_name,
            'address': company.address,
            'phone': company.phone,
            'email': company.email,
            'company_description': company.company_description,
            'logo_path': company.logo_path
        })
    return jsonify({}), 404

@own_company.route('/api/company_info', methods=['POST'])
def create_company_info():
    """创建公司信息API"""
    data = request.get_json()
    company = CompanyInfo(
        company_name=data.get('company_name', ''),
        company_name_cn=data.get('company_name_cn'),
        company_short_name=data.get('company_short_name'),
        address=data.get('address', ''),
        phone=data.get('phone', ''),
        email=data.get('email', ''),
        company_description=data.get('company_description', ''),
        logo_path=data.get('logo_path')
    )
    db.session.add(company)
    db.session.commit()
    return jsonify({
        'id': company.id,
        'company_name': company.company_name,
        'company_name_cn': company.company_name_cn,
        'company_short_name': company.company_short_name,
        'address': company.address,
        'phone': company.phone,
        'email': company.email,
        'company_description': company.company_description,
        'logo_path': company.logo_path
    })

@own_company.route('/api/company_info/<int:company_id>', methods=['PUT'])
def update_company_info_api(company_id):
    """更新公司信息API"""
    company = CompanyInfo.query.get_or_404(company_id)
    data = request.get_json()
    
    company.company_name = data.get('company_name', company.company_name)
    company.company_name_cn = data.get('company_name_cn', company.company_name_cn)
    company.company_short_name = data.get('company_short_name', company.company_short_name)
    company.address = data.get('address', company.address)
    company.phone = data.get('phone', company.phone)
    company.email = data.get('email', company.email)
    company.company_description = data.get('company_description', company.company_description)
    company.logo_path = data.get('logo_path', company.logo_path)
    
    db.session.commit()
    return jsonify({
        'id': company.id,
        'company_name': company.company_name,
        'company_name_cn': company.company_name_cn,
        'company_short_name': company.company_short_name,
        'address': company.address,
        'phone': company.phone,
        'email': company.email,
        'company_description': company.company_description,
        'logo_path': company.logo_path
    })

@own_company.route('/company/edit', methods=['GET', 'POST'])
@csrf.exempt  # 暂时豁免CSRF，后续可以改进
def edit_company_info():
    """编辑公司信息"""
    company = CompanyInfo.query.first()
    
    if request.method == 'POST':
        try:
            if company is None:
                company = CompanyInfo()
            
            company.company_name = request.form['company_name']
            company.company_name_cn = request.form.get('company_name_cn', '')
            company.company_short_name = request.form.get('company_short_name', '')
            company.company_description = request.form['company_description']
            company.phone = request.form['phone']
            company.email = request.form['email']
            company.address = request.form['address']
            
            # 处理logo上传
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo and logo.filename != '':
                    # 确保文件名安全
                    from werkzeug.utils import secure_filename
                    
                    # 获取文件扩展名
                    filename = secure_filename(logo.filename)
                    name, ext = os.path.splitext(filename)
                    
                    # 使用固定的文件名（确保本地和服务器路径一致）
                    # 如果已有logo，保持原有的文件名；否则使用 company_logo + 扩展名
                    if company.logo_path:
                        # 使用现有的文件名
                        existing_filename = os.path.basename(company.logo_path)
                        # 如果扩展名不同，更新扩展名
                        existing_name, existing_ext = os.path.splitext(existing_filename)
                        if existing_ext.lower() != ext.lower():
                            new_filename = f'{existing_name}{ext}'
                        else:
                            new_filename = existing_filename
                    else:
                        # 首次上传，使用固定文件名
                        new_filename = f'company_logo{ext}'
                    
                    # 构建保存路径（相对于 App_new/static）
                    logo_relative_path = os.path.join('company', new_filename).replace('\\', '/')
                    
                    # 构建完整的文件系统路径
                    full_path = os.path.join('App_new', 'static', 'company', new_filename)
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # 如果文件已存在，删除旧文件
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        print(f"🗑️ 删除旧Logo: {full_path}")
                    
                    # 保存文件
                    logo.save(full_path)
                    
                    # 保存相对路径到数据库（不包含App_new/static前缀）
                    company.logo_path = logo_relative_path
                    
                    print(f"✅ Logo保存成功: {full_path}")
                    print(f"✅ 数据库路径: {logo_relative_path}")
            
            if company.id is None:
                db.session.add(company)
            
            db.session.commit()
            
            flash('公司信息更新成功！', 'success')
            return redirect(url_for('own_company.edit_company_info'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 更新失败: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'更新失败：{str(e)}', 'error')
    
    # 如果是现有记录，确保显示时路径格式正确
    if company and company.logo_path:
        path = normalize_path(company.logo_path)
        # 移除可能存在的多余前缀
        path = path.replace('App_new/static/', '')
        path = path.replace('static/', '')
        # 如果路径不包含 'company/' 前缀，且不是绝对路径，则添加 'company/' 前缀
        if not path.startswith('company/') and not os.path.isabs(path):
            # 检查是否是文件名（不包含路径分隔符）
            if '/' not in path and '\\' not in path:
                path = os.path.join('company', path).replace('\\', '/')
        company.logo_path = path
    
    return render_template('shared/own_company/own_company_form.html', company=company)

@own_company.route('/company_header')
def company_header():
    company = CompanyInfo.query.first()
    if company and company.logo_path:
        path = normalize_path(company.logo_path)
        path = path.replace('App_new/static/', '')
        path = path.replace('static/', '')
        # 如果路径不包含 'company/' 前缀，且不是绝对路径，则添加 'company/' 前缀
        if not path.startswith('company/') and not os.path.isabs(path):
            # 检查是否是文件名（不包含路径分隔符）
            if '/' not in path and '\\' not in path:
                path = os.path.join('company', path).replace('\\', '/')
        company.logo_path = path
    return render_template('shared/own_company/own_company_header.html', company=company)