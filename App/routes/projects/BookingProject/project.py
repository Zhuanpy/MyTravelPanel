from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from App.models.projects.BookingProject import db, ProjectHeader, ProjectRef, ProjectEO
from App.models.Product.Suppliers import Supplier
from App.models.Product.BusinessType import BusinessType
from App.forms.header_forms import ProjectHeaderForm
from App.forms.ref_forms import ProjectRefForm
from App.forms.eo_forms import ProjectEOForm
from datetime import datetime
from sqlalchemy import func
import traceback  # 添加traceback模块

projects = Blueprint('projects', __name__)

@projects.route('/header/create', methods=['GET', 'POST'])
def create_header():
    form = ProjectHeaderForm()
    
    if form.validate_on_submit():
        try:
            hid = ProjectHeader.generate_hid()
            
            # 处理公司信息
            company_id = None
            company_name = form.company_name.data
            
            if form.company_id.data and form.company_id.data != 0:
                company_id = form.company_id.data
                # 如果选择了公司，使用公司的名称
                from App.models.projects.BookingProject import CustomerCompany
                selected_company = CustomerCompany.query.get(company_id)
                if selected_company:
                    company_name = selected_company.company_name
            
            header = ProjectHeader(
                hid=hid,
                desc=form.desc.data,
                company_id=company_id,
                company_name=company_name,
                limit=form.limit.data,
                contact=form.contact.data,
                dept=form.dept.data,
                staff_id=form.staff_id.data if form.staff_id.data else None,
                staff_name=form.staff_name.data,
                currency=form.currency.data,
                type=form.type.data,
                source=form.source.data,
                country=form.country.data,
                status=form.status.data,
                remarks=form.remarks.data
            )
            db.session.add(header)
            db.session.commit()
            flash('项目主表创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充项目编号
    hid = ProjectHeader.generate_hid()
    form.hid.data = hid
    
    return render_template('projects/BookingProject/create_header.html', form=form, hid=hid)

@projects.route('/header/<int:header_id>')
def header_detail(header_id):
    header = ProjectHeader.query.get_or_404(header_id)
    return render_template('projects/BookingProject/header_detail.html', header=header)

@projects.route('/ref/create/<int:header_id>', methods=['GET', 'POST'])
def create_ref(header_id):
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectRefForm()
    form.header_id.data = header_id
    
    if form.validate_on_submit():
        try:
            ref_number = ProjectRef.generate_ref_number(header.hid)
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=form.name.data,
                ref_type_id=form.ref_type_id.data,
                description=form.description.data,
                supplier_id=form.supplier_id.data if form.supplier_id.data and form.supplier_id.data != 0 else None,
                supplier_contact=form.supplier_contact.data,
                supplier_phone=form.supplier_phone.data,
                selling_price=form.selling_price.data,
                cost_price=form.cost_price.data,
                currency=form.currency.data,
                expected_delivery_date=form.expected_delivery_date.data,
                actual_delivery_date=form.actual_delivery_date.data,
                remarks=form.remarks.data,
                status=form.status.data,
                payment_status=form.payment_status.data
            )
            db.session.add(ref)
            db.session.commit()
            flash('REF明细创建成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充REF编号
    ref_number = ProjectRef.generate_ref_number(header.hid)
    form.ref_number.data = ref_number
    
    # 获取业务类型和供应商数据
    business_types = BusinessType.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('projects/BookingProject/create_ref.html',
                           form=form, 
                           header=header, 
                           ref_number=ref_number,
                         business_types=business_types,
                         suppliers=suppliers)

@projects.route('/ref/<int:ref_id>')
def ref_detail(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    return render_template('projects/BookingProject/ref_detail.html', ref=ref)

@projects.route('/eo/create/<int:ref_id>', methods=['GET', 'POST'])
def create_eo(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    form = ProjectEOForm()
    form.ref_id.data = ref_id
    
    if form.validate_on_submit():
        try:
            eo_number = ProjectEO.generate_eo_number(ref.ref_number)
            eo = ProjectEO(
                ref_id=ref.id,
                eo_number=eo_number,
                name=form.name.data,
                supplier_type=form.supplier_type.data,
                supplier_id=form.supplier_id.data,
                external_system=form.external_system.data,
                external_status=form.external_status.data,
                external_reference=form.external_reference.data,
                amount=form.amount.data,
                currency=form.currency.data,
                remarks=form.remarks.data,
                status=form.status.data
            )
            db.session.add(eo)
            db.session.commit()
            flash('EO子明细创建成功！', 'success')
            return redirect(url_for('projects.ref_detail', ref_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充EO编号
    eo_number = ProjectEO.generate_eo_number(ref.ref_number)
    form.eo_number.data = eo_number
    
    return render_template('projects/BookingProject/create_eo.html',
                           form=form, ref=ref, eo_number=eo_number)

@projects.route('/')
def list_projects():
    status = request.args.get('status')
    query = ProjectHeader.query

    if status:
        query = query.filter(ProjectHeader.status == status)
    
    projects = query.order_by(ProjectHeader.created_at.desc()).all()
    return render_template('projects/BookingProject/list_projects.html', projects=projects)

@projects.route('/statistics')
def project_statistics():
    # 获取项目总数
    total_projects = ProjectHeader.query.count()
    
    # 按状态统计项目数量
    status_stats = db.session.query(
        ProjectHeader.status,
        func.count(ProjectHeader.id)
    ).group_by(ProjectHeader.status).all()
    
    # 按月统计项目数量（最近12个月）
    monthly_stats = db.session.query(
        func.date_format(ProjectHeader.created_at, '%Y-%m'),
        func.count(ProjectHeader.id)
    ).group_by(
        func.date_format(ProjectHeader.created_at, '%Y-%m')
    ).order_by(
        func.date_format(ProjectHeader.created_at, '%Y-%m').desc()
    ).limit(12).all()
    
    # 统计REF类型分布
    ref_type_stats = db.session.query(
        BusinessType.name,
        func.count(ProjectRef.id)
    ).join(ProjectRef.ref_type).group_by(BusinessType.name).all()
    
    # 统计供应商类型分布
    supplier_type_stats = db.session.query(
        ProjectEO.supplier_type,
        func.count(ProjectEO.id)
    ).group_by(ProjectEO.supplier_type).all()
    
    return render_template('projects/statistics.html',
                         total_projects=total_projects,
                         status_stats=status_stats,
                         monthly_stats=monthly_stats,
                         ref_type_stats=ref_type_stats,
                         supplier_type_stats=supplier_type_stats)

@projects.route('/header/<int:header_id>/edit', methods=['GET', 'POST'])
def edit_header(header_id):
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectHeaderForm(obj=header)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(header)
            db.session.commit()
            flash('项目主表更新成功！', 'success')
            return redirect(url_for('projects.header_detail', header_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_header.html', form=form, header=header)

@projects.route('/ref/<int:ref_id>/edit', methods=['GET', 'POST'])
def edit_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    form = ProjectRefForm(obj=ref)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(ref)
            db.session.commit()
            flash('REF明细更新成功！', 'success')
            return redirect(url_for('projects.ref_detail', ref_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_ref.html', form=form, ref=ref)

@projects.route('/eo/<int:eo_id>/edit', methods=['GET', 'POST'])
def edit_eo(eo_id):
    eo = ProjectEO.query.get_or_404(eo_id)
    form = ProjectEOForm(obj=eo)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(eo)
            db.session.commit()
            flash('EO子明细更新成功！', 'success')
            return redirect(url_for('projects.eo_detail', eo_id=eo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('projects/BookingProject/edit_eo.html', form=form, eo=eo)

@projects.route('/eo/<int:eo_id>')
def eo_detail(eo_id):
    eo = ProjectEO.query.get_or_404(eo_id)
    return render_template('projects/BookingProject/eo_detail.html', eo=eo)

@projects.route('/generate_ref_number/<project_hid>', methods=['GET'])
def generate_ref_number(project_hid):
    """生成新的REF编号"""
    try:
        print(f"Generating REF number for project HID: {project_hid}")
        ref_number = ProjectRef.generate_ref_number(project_hid)
        print(f"Generated REF number: {ref_number}")
        return jsonify({'ref_number': ref_number})
    except Exception as e:
        error_details = traceback.format_exc()
        print("Error generating REF number:", error_details)
        return jsonify({
            'error': str(e),
            'details': error_details
        }), 400 

@projects.route('/ref/delete/<int:ref_id>', methods=['POST', 'GET'])
def delete_ref(ref_id):
    ref = ProjectRef.query.get_or_404(ref_id)
    header_id = ref.header_id
    db.session.delete(ref)
    db.session.commit()
    flash('REF明细已删除', 'success')
    return redirect(url_for('projects.header_detail', header_id=header_id)) 