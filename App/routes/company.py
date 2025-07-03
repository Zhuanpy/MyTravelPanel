from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from App.exts import db
from App.models.projects.BookingProject import CustomerCompany
from App.forms.company_forms import CustomerCompanyForm
from sqlalchemy import or_

company = Blueprint('company', __name__)

@company.route('/')
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
                created_by='admin'  # 这里可以从session获取当前用户
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
def company_detail(company_id):
    """公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    return render_template('company/company_detail.html', company=company)

@company.route('/<int:company_id>/edit', methods=['GET', 'POST'])
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
def api_company_detail(company_id):
    """API获取公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    return jsonify(company.to_dict()) 