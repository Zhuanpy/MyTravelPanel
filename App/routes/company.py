from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from App.exts import db
from App.models.projects.BookingProject import CustomerCompany
from App.forms.company_forms import CustomerCompanyForm
from App.utils.decorators import staff_only
from sqlalchemy import or_
import pandas as pd
import io
import os
from datetime import datetime

company = Blueprint('company', __name__)

@company.route('/')
@login_required
@staff_only
def list_companies():
    """公司列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = CustomerCompany.query
    
    if search:
        query = query.filter(
            or_(
                CustomerCompany.company_name.ilike(f'%{search}%'),
                CustomerCompany.contact_person.ilike(f'%{search}%'),
                CustomerCompany.company_code.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter(CustomerCompany.status == status)
    
    companies = query.order_by(CustomerCompany.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('company/list_companies.html', companies=companies)

@company.route('/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_company():
    """创建公司"""
    form = CustomerCompanyForm()
    
    if form.validate_on_submit():
        try:
            company = CustomerCompany(
                company_name=form.company_name.data,
                company_code=form.company_code.data,
                contact_person=form.contact_person.data,
                contact_phone=form.contact_phone.data,
                contact_email=form.contact_email.data,
                address=form.address.data,
                industry=form.industry.data,
                company_size=form.company_size.data,
                credit_limit=form.credit_limit.data,
                currency=form.currency.data,
                status=form.status.data,
                remarks=form.remarks.data,
                created_by=current_user.username if current_user.is_authenticated else 'system'
            )
            db.session.add(company)
            db.session.commit()
            flash('公司创建成功！', 'success')
            return redirect(url_for('company.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('company/create_company.html', form=form)

@company.route('/<int:company_id>')
@login_required
@staff_only
def company_detail(company_id):
    """公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    return render_template('company/company_detail.html', company=company)

@company.route('/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_company(company_id):
    """编辑公司"""
    company = CustomerCompany.query.get_or_404(company_id)
    form = CustomerCompanyForm(obj=company)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(company)
            db.session.commit()
            flash('公司信息更新成功！', 'success')
            return redirect(url_for('company.company_detail', company_id=company.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('company/edit_company.html', form=form, company=company)

@company.route('/<int:company_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_company(company_id):
    """删除公司"""
    company = CustomerCompany.query.get_or_404(company_id)
    try:
        db.session.delete(company)
        db.session.commit()
        flash('公司删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('company.list_companies'))

@company.route('/api/search')
@login_required
@staff_only
def api_search_companies():
    """API搜索公司（用于下拉选择）"""
    search = request.args.get('q', '')
    companies = CustomerCompany.query.filter(
        CustomerCompany.company_name.ilike(f'%{search}%')
    ).limit(10).all()
    
    return jsonify([{
        'id': company.id,
        'text': company.company_name,
        'contact_person': company.contact_person,
        'contact_phone': company.contact_phone
    } for company in companies])

@company.route('/api/<int:company_id>')
@login_required
@staff_only
def api_company_detail(company_id):
    """API获取公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    return jsonify(company.to_dict())

@company.route('/download-template')
@login_required
@staff_only
def download_template():
    """下载Excel模板"""
    # 创建示例数据
    sample_data = [
        ['公司名称 *', '公司代码', '联系人', '联系电话', '邮箱', '行业', '规模', '状态'],
        ['示例公司A', 'CODE001', '张三', '13800138000', 'zhangsan@example.com', '科技', '中型公司', 'active'],
        ['示例公司B', 'CODE002', '李四', '13800138001', 'lisi@example.com', '金融', '大型公司', 'active'],
        ['', '', '', '', '', '', '', ''],  # 空行供用户填写
        ['', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', ''],
    ]
    
    # 创建DataFrame
    df = pd.DataFrame(sample_data)
    
    # 创建Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='公司信息', index=False, header=False)
        
        # 获取工作表
        worksheet = writer.sheets['公司信息']
        
        # 设置列宽
        column_widths = [20, 15, 15, 15, 25, 15, 15, 10]
        for i, width in enumerate(column_widths):
            worksheet.column_dimensions[chr(65 + i)].width = width
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'公司信息导入模板_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@company.route('/import-excel', methods=['POST'])
@login_required
@staff_only
def import_excel():
    """导入Excel数据"""
    try:
        data = request.get_json()
        companies_data = data.get('companies', [])
        
        if not companies_data:
            return jsonify({
                'success': False,
                'message': '没有数据可导入'
            })
        
        success_count = 0
        error_count = 0
        errors = []
        
        for i, company_data in enumerate(companies_data, 1):
            try:
                # 验证必填字段
                if not company_data.get('company_name'):
                    errors.append(f'第{i}行：公司名称不能为空')
                    error_count += 1
                    continue
                
                # 检查公司名称是否已存在
                existing_company = CustomerCompany.query.filter_by(
                    company_name=company_data['company_name']
                ).first()
                
                if existing_company:
                    errors.append(f'第{i}行：公司名称"{company_data["company_name"]}"已存在')
                    error_count += 1
                    continue
                
                # 验证行业
                industry = company_data.get('industry', '').strip()
                valid_industries = ['科技', '金融', '制造业', '医疗健康', '教育', '零售', '旅游', '房地产', '咨询', '其他']
                if industry and industry not in valid_industries:
                    # 尝试映射英文到中文
                    industry_map = {
                        'technology': '科技',
                        'finance': '金融',
                        'manufacturing': '制造业',
                        'healthcare': '医疗健康',
                        'education': '教育',
                        'retail': '零售',
                        'tourism': '旅游',
                        'real_estate': '房地产',
                        'consulting': '咨询',
                        'other': '其他'
                    }
                    industry = industry_map.get(industry.lower(), '其他')
                
                # 验证规模
                size = company_data.get('company_size', '').strip()
                valid_sizes = ['初创公司', '小型公司', '中型公司', '大型公司', '企业级']
                if size and size not in valid_sizes:
                    # 尝试映射英文到中文
                    size_map = {
                        'startup': '初创公司',
                        'small': '小型公司',
                        'medium': '中型公司',
                        'large': '大型公司',
                        'enterprise': '企业级'
                    }
                    size = size_map.get(size.lower(), '中型公司')
                
                # 验证状态
                status = company_data.get('status', 'active').strip()
                valid_statuses = ['active', 'inactive', 'suspended']
                if status not in valid_statuses:
                    status = 'active'
                
                # 创建公司记录
                company = CustomerCompany(
                    company_name=company_data['company_name'],
                    company_code=company_data.get('company_code', ''),
                    contact_person=company_data.get('contact_person', ''),
                    contact_phone=company_data.get('contact_phone', ''),
                    contact_email=company_data.get('email', ''),
                    industry=industry,
                    company_size=size,
                    status=status,
                    created_by='admin'  # 这里可以从session获取当前用户
                )
                
                db.session.add(company)
                success_count += 1
                
            except Exception as e:
                errors.append(f'第{i}行：{str(e)}')
                error_count += 1
        
        # 提交所有成功的数据
        if success_count > 0:
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功导入{success_count}条记录，失败{error_count}条',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}'
        }) 