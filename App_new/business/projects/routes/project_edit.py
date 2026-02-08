
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.invoice import ProjectInvoice
from ..services.project_service import ProjectService
from ..forms.project_forms import ProjectEditForm
from App_new.utils.decorators import staff_only
from App_new.exts import db
from datetime import datetime
import traceback

# 创建蓝图
bp = Blueprint('edit', __name__)

@bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_project(project_id):
    """编辑项目"""
    try:
        project_service = ProjectService()

        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            flash('项目不存在', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 获取客户公司列表
        companies = CustomerCompany.query.filter_by(status='active').order_by(CustomerCompany.company_name).all()

        form = ProjectEditForm(obj=project)
        form.company_id.choices = [(0, '选择客户公司')] + [(c.id, c.company_name) for c in companies]

        if request.method == 'POST':
            if form.validate_on_submit():
                # 准备更新数据
                update_data = {
                    'desc': form.description.data,
                    'company_id': form.company_id.data if form.company_id.data != 0 else None,
                    'contact': form.contact.data,
                    'contact_phone': form.contact_phone.data,
                    'contact_email': form.contact_email.data,
                    'type': form.type.data,
                    'status': form.status.data,
                    'currency': form.currency.data,
                    'leader_name': form.leader_name.data,
                    'remarks': form.remarks.data,
                    'updated_at': datetime.utcnow(),
                    'last_updated_by': current_user.username if hasattr(current_user, 'username') else 'system'
                }

                # 更新项目
                success = project_service.update_project(project_id, update_data)

                if success:
                    # 同步更新关联发票的客户公司信息
                    new_company_id = form.company_id.data if form.company_id.data != 0 else None
                    if new_company_id:
                        company = CustomerCompany.query.get(new_company_id)
                        new_company_name = company.company_name if company else None
                    else:
                        new_company_name = '个人'

                    ProjectInvoice.query.filter_by(header_id=project_id).update(
                        {'customer_company': new_company_name}
                    )
                    db.session.commit()

                    flash(f'项目 {project.hid} 更新成功！', 'success')
                    return redirect(url_for('business_projects.detail.project_detail', project_id=project_id))
                else:
                    flash('项目更新失败，请重试', 'error')
            else:
                # 显示表单验证错误
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{getattr(form, field).label.text}: {error}', 'error')

        return render_template(
            'business/projects/project_edit.html',
            form=form,
            project=project,
            companies=companies
        )

    except Exception as e:
        flash(f'编辑项目失败：{str(e)}', 'error')
        traceback.print_exc()
        return redirect(url_for('business_projects.list.list_projects'))

@bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_project(project_id):
    """删除项目"""
    try:
        project_service = ProjectService()

        # 获取项目信息
        project = project_service.get_project_by_id(project_id)
        if not project:
            flash('项目不存在', 'error')
            return redirect(url_for('business_projects.list.list_projects'))

        # 检查项目是否可以删除
        if not project_service.can_delete_project(project_id):
            flash('项目包含关联数据，无法删除', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=project_id))

        # 删除项目
        success = project_service.delete_project(project_id)

        if success:
            flash(f'项目 {project.hid} 删除成功！', 'success')
            return redirect(url_for('business_projects.list.list_projects'))
        else:
            flash('项目删除失败，请重试', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=project_id))

    except Exception as e:
        flash(f'删除项目失败：{str(e)}', 'error')
        traceback.print_exc()
        return redirect(url_for('business_projects.list.list_projects'))

@bp.route('/<int:project_id>/status', methods=['POST'])
@login_required
@staff_only
def update_project_status(project_id):
    """更新项目状态"""
    try:
        new_status = request.form.get('status')
        if not new_status:
            return jsonify({'success': False, 'error': '状态参数缺失'}), 400

        project_service = ProjectService()

        # 更新项目状态
        success = project_service.update_project_status(project_id, new_status)

        if success:
            return jsonify({
                'success': True,
                'message': '项目状态更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '项目状态更新失败'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:project_id>/duplicate', methods=['POST'])
@login_required
@staff_only
def duplicate_project(project_id):
    """复制项目"""
    try:
        project_service = ProjectService()

        # 复制项目
        new_project = project_service.duplicate_project(project_id)

        if new_project:
            flash(f'项目复制成功！新项目编号: {new_project.hid}', 'success')
            return redirect(url_for('business_projects.detail.project_detail', project_id=new_project.id))
        else:
            flash('项目复制失败，请重试', 'error')
            return redirect(url_for('business_projects.detail.project_detail', project_id=project_id))

    except Exception as e:
        flash(f'复制项目失败：{str(e)}', 'error')
        traceback.print_exc()
        return redirect(url_for('business_projects.detail.project_detail', project_id=project_id))
