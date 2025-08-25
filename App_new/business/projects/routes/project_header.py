from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.exts import csrf, db
from App_new.business.projects.forms.project_forms import ProjectHeaderForm
from App_new.utils.decorators import staff_only, admin_only
from datetime import datetime
from sqlalchemy import func
import traceback
import json

project_header = Blueprint('project_header', __name__)

@project_header.route('/create', methods=['GET', 'POST'])
@login_required
def create_header():
    """重定向到新的项目创建页面"""
    return redirect(url_for('business_projects.project_create.create_header'))

@project_header.route('/<int:header_id>')
@login_required
@staff_only
def header_detail(header_id):
    """项目头部详情页面"""
    header = ProjectHeader.query.get_or_404(header_id)
    
    # 手动加载相关的REF数据
    refs = ProjectRef.query.filter_by(header_id=header_id).all()
    header.refs = refs
    
    # 获取上一个和下一个项目（优化查询）
    prev_header = ProjectHeader.query.filter(
        ProjectHeader.id < header_id
    ).order_by(ProjectHeader.id.desc()).limit(1).first()
    
    next_header = ProjectHeader.query.filter(
        ProjectHeader.id > header_id
    ).order_by(ProjectHeader.id.asc()).limit(1).first()
    
    # 获取公司信息（通过backref自动关联）
    company = header.company
    
    # 获取所有活跃的公司列表供选择
    companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()
    
    return render_template('business/projects/project_header/header_detail.html', 
                         header=header, 
                         company=company,
                         companies=companies,
                         prev_header=prev_header, 
                         next_header=next_header)

@project_header.route('/<int:header_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_header(header_id):
    """编辑项目头部"""
    header = ProjectHeader.query.get_or_404(header_id)
    form = ProjectHeaderForm(obj=header)
    
    if form.validate_on_submit():
        try:
            # 处理company_id字段，将0转换为None
            if form.company_id.data == 0:
                header.company_id = None
            else:
                header.company_id = form.company_id.data
            
            # 更新其他字段
            header.hid = form.hid.data
            header.desc = form.desc.data
            header.limit = form.limit.data
            header.contact = form.contact.data
            header.dept = form.dept.data
            header.staff_id = form.staff_id.data if form.staff_id.data else None
            header.staff_name = form.staff_name.data
            header.leader_name = form.leader_name.data
            header.currency = form.currency.data
            header.type = form.type.data
            header.source = form.source.data
            header.country = form.country.data
            header.status = form.status.data
            header.remarks = form.remarks.data
            
            db.session.commit()
            return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('business/projects/project_header/edit_header.html', form=form, header=header)

@project_header.route('/<int:header_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_header(header_id):
    """删除项目主表（幂等设计：不存在也视为删除成功）"""
    try:
        header = ProjectHeader.query.get(header_id)

        if not header:
            # 已被删除或不存在，按成功返回，避免前端出现404提示
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '项目不存在或已删除'})
            else:
                flash('项目不存在或已删除', 'success')
                return redirect(url_for('business_projects.list.list_projects'))

        # 删除所有相关的EO（通过REF关联）
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.eo import ProjectEO
        refs = ProjectRef.query.filter_by(header_id=header_id).all()
        for ref in refs:
            # 删除该REF下的所有EO
            eos = ProjectEO.query.filter_by(ref_id=ref.id).all()
            for eo in eos:
                db.session.delete(eo)
            # 删除REF
            db.session.delete(ref)

        # 删除项目主表
        db.session.delete(header)
        db.session.commit()

        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '项目已成功删除'})
        else:
            flash('项目已成功删除', 'success')
            return redirect(url_for('business_projects.list.list_projects'))

    except Exception as e:
        db.session.rollback()
        error_msg = f'删除失败：{str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

@project_header.route('/update_desc', methods=['POST'])
@csrf.exempt
def update_header_desc():
    """更新项目描述"""
    data = request.get_json()
    header_id = data.get('header_id')
    desc = data.get('desc', '').strip()
    if not header_id or not desc:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.desc = desc
    db.session.commit()
    return jsonify({'success': True}) 

@project_header.route('/update_company', methods=['POST'])
@csrf.exempt
def update_header_company():
    """更新项目公司"""
    data = request.get_json()
    header_id = data.get('header_id')
    company_id = data.get('company_id')
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    
    # 处理company_id，将0或空值转换为None
    if not company_id or company_id == 0:
        header.company_id = None
    else:
        header.company_id = company_id
    
    db.session.commit()
    return jsonify({'success': True})

@project_header.route('/update_status', methods=['POST'])
@csrf.exempt
def update_header_status():
    """更新项目状态"""
    data = request.get_json()
    project_id = data.get('project_id')
    status = data.get('status')
    csrf_token = data.get('csrf_token')
    
    if not project_id or not status:
        return jsonify({'success': False, 'message': '参数错误'})
    
    # 验证CSRF token
    if not csrf_token:
        return jsonify({'success': False, 'message': 'CSRF token缺失'})
    
    header = ProjectHeader.query.get(project_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    
    # 验证状态值
    valid_statuses = ['draft', 'active', 'completed', 'cancelled']
    if status not in valid_statuses:
        return jsonify({'success': False, 'message': '无效的状态值'})
    
    try:
        header.status = status
        db.session.commit()
        return jsonify({'success': True, 'message': '状态更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}) 

@project_header.route('/update_contact', methods=['POST'])
@csrf.exempt
def update_header_contact():
    """更新项目联系人"""
    data = request.get_json()
    header_id = data.get('header_id')
    contact = data.get('contact')
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.contact = contact
    db.session.commit()
    return jsonify({'success': True})

@project_header.route('/update_remarks', methods=['POST'])
@csrf.exempt
def update_header_remarks():
    """更新项目备注"""
    data = request.get_json()
    header_id = data.get('header_id')
    remarks = data.get('remarks', '').strip()
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误'})
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': '项目不存在'})
    header.remarks = remarks
    db.session.commit()
    return jsonify({'success': True}) 



