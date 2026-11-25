from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only
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
            'logo_path': company.logo_path,
            'website': company.website
        })
    return jsonify({}), 404

@own_company.route('/api/company_info', methods=['POST'])
@login_required
@staff_only
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
        logo_path=data.get('logo_path'),
        website=data.get('website')
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
        'logo_path': company.logo_path,
        'website': company.website
    })

@own_company.route('/api/company_info/<int:company_id>', methods=['PUT'])
@login_required
@staff_only
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
    company.website = data.get('website', company.website)

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
        'logo_path': company.logo_path,
        'website': company.website
    })

@own_company.route('/company/info')
def company_info():
    """公司信息展示页面"""
    company = CompanyInfo.query.first()
    if company and company.logo_path:
        path = normalize_path(company.logo_path)
        path = path.replace('App_new/static/', '')
        path = path.replace('static/', '')
        if not path.startswith('company/') and not os.path.isabs(path):
            if '/' not in path and '\\' not in path:
                path = os.path.join('company', path).replace('\\', '/')
        company.logo_path = path

    # 付款配置
    from App_new.shared.models.system_config import SystemConfig
    payment_config = SystemConfig.get_payment_config()

    return render_template('shared/own_company/own_company_info.html', company=company, payment_config=payment_config)

# 公司名称、银行收款信息、logo 都会印到发票上：必须登录的员工才能改，且不再豁免 CSRF
@own_company.route('/company/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_company_info():
    """编辑公司信息"""
    from App_new.shared.models.system_config import SystemConfig
    company = CompanyInfo.query.first()

    if request.method == 'POST':
        try:
            # 保存付款配置
            SystemConfig.set('payment_bank_name', request.form.get('payment_bank_name', ''), '收款银行名称')
            SystemConfig.set('payment_account_name', request.form.get('payment_account_name', ''), '收款账户名')
            SystemConfig.set('payment_account_number', request.form.get('payment_account_number', ''), '收款账号')
            SystemConfig.set('payment_note', request.form.get('payment_note', ''), '付款备注说明')

            # 处理付款二维码上传
            import uuid
            qr_file = request.files.get('payment_qr_image')
            if qr_file and qr_file.filename:
                from flask import current_app
                ext = os.path.splitext(qr_file.filename)[1].lower()
                filename = f"payment_qr_{uuid.uuid4().hex[:8]}{ext}"
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'config')
                os.makedirs(upload_dir, exist_ok=True)
                qr_file.save(os.path.join(upload_dir, filename))
                SystemConfig.set('payment_qr_image', f'uploads/config/{filename}', '付款二维码图片路径')
            if company is None:
                company = CompanyInfo()
            
            company.company_name = request.form['company_name']
            company.company_name_cn = request.form.get('company_name_cn', '')
            company.company_short_name = request.form.get('company_short_name', '')
            company.company_description = request.form['company_description']
            company.phone = request.form['phone']
            company.email = request.form['email']
            company.address = request.form['address']
            company.website = request.form.get('website', '')
            company.ta_license = request.form.get('ta_license', '')
            company.uen = request.form.get('uen', '')

            # 处理 logo / 电子章上传
            # 每次上传用新文件名（带时间戳）：静态图片被 nginx 设了 30 天缓存，
            # 沿用旧文件名的话 URL 不变，浏览器一直显示缓存里的旧图，看起来像"没保存成功"。
            # 保存到 current_app.static_folder，不依赖 gunicorn 的工作目录。
            # 旧图片文件保留不删（体积很小；删了无法恢复）。
            from flask import current_app
            from datetime import datetime as _dt

            def _save_company_image(field, prefix):
                """保存上传的图片到 static/company/，返回新的相对路径；没上传返回 None"""
                f = request.files.get(field)
                if not f or not f.filename:
                    return None
                ext = os.path.splitext(f.filename)[1].lower() or '.png'
                if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
                    raise ValueError(f'不支持的图片格式: {ext}')
                new_filename = f"{prefix}_{_dt.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                save_dir = os.path.join(current_app.static_folder, 'company')
                os.makedirs(save_dir, exist_ok=True)
                f.save(os.path.join(save_dir, new_filename))
                return f'company/{new_filename}'

            new_logo = _save_company_image('logo', 'company_logo')
            if new_logo:
                company.logo_path = new_logo
                current_app.logger.info(f"公司logo已更新: {new_logo}")

            new_stamp = _save_company_image('stamp', 'company_stamp')
            if new_stamp:
                company.stamp_path = new_stamp
                current_app.logger.info(f"公司电子章已更新: {new_stamp}")

            if company.id is None:
                db.session.add(company)
            
            db.session.commit()

            flash('公司信息更新成功！', 'success')
            return redirect(url_for('own_company.company_info'))
            
        except Exception as e:
            db.session.rollback()
            # 用 logger 而不是带 emoji 的 print：Windows 中文控制台(GBK)打印 emoji 会抛错，把保存本身搞失败
            current_app.logger.exception(f"公司信息更新失败: {e}")
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
    
    payment_config = SystemConfig.get_payment_config()
    return render_template('shared/own_company/own_company_form.html', company=company, payment_config=payment_config)

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