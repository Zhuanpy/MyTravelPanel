# -*- coding: utf-8 -*-
"""
项目创建路由
基于旧app的create_header实现，使用project_header模板
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.forms.project_forms import ProjectHeaderForm
from App_new.utils.decorators import staff_only
from App_new.exts import db
from datetime import datetime
import traceback

# 创建蓝图
project_create = Blueprint('project_create', __name__)

@project_create.route('/', methods=['GET', 'POST'])
@login_required
@staff_only
def create_header():
    """创建新项目（HID项目）- 基于旧app的实现"""
    form = ProjectHeaderForm()
    
    if form.validate_on_submit():
        try:
            # 生成HID（不需要事务包装）
            hid = ProjectHeader.generate_hid()
            
            # 处理公司信息
            company_id = None
            if form.company_id.data and form.company_id.data != 0:
                company_id = form.company_id.data
            
            # 如果负责人姓名为空，自动使用经办人姓名
            leader_name = form.leader_name.data if form.leader_name.data else form.staff_name.data
            
            header = ProjectHeader(
                hid=hid,
                desc=form.desc.data,
                company_id=company_id,
                limit=form.limit.data,
                contact=form.contact.data,
                dept=form.dept.data,
                staff_id=current_user.id if current_user.is_authenticated else None,
                staff_name=form.staff_name.data,
                leader_name=leader_name,
                currency=form.currency.data,
                type=form.type.data,
                source=form.source.data,
                country=form.country.data,
                status=form.status.data,
                remarks=form.remarks.data,
                reminder_event=form.reminder_event.data,
                reminder_date=form.reminder_date.data
            )
            db.session.add(header)
            db.session.commit()
            
            # 如果有提醒信息，同步到待办事项
            if header.reminder_event and header.reminder_date:
                from App_new.utils.reminder_utils import create_reminder_todo
                create_reminder_todo(header)
            
            flash('项目主表创建成功！', 'success')
            return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充项目编号
    try:
        # 直接调用，不需要事务包装
        print("DEBUG: 开始生成HID...")  # 调试信息
        hid = ProjectHeader.generate_hid()
        form.hid.data = hid
        print(f"DEBUG: 生成的HID: {hid}")  # 调试信息
    except Exception as e:
        # 如果生成HID失败，使用默认值
        hid = "H1"
        form.hid.data = hid
        flash(f'生成项目编号失败，使用默认编号：{hid}，错误：{str(e)}', 'warning')
        print(f"DEBUG: HID生成失败: {e}")  # 调试信息
        print(f"DEBUG: 错误类型: {type(e)}")  # 调试信息
        import traceback
        print(f"DEBUG: 错误堆栈: {traceback.format_exc()}")  # 调试信息
    
    # 预填充经办人姓名（当前登录用户）
    if current_user.is_authenticated:
        if hasattr(current_user, 'profile') and current_user.profile and current_user.profile.get_full_name() != "未设置姓名":
            form.staff_name.data = current_user.profile.get_full_name()
        else:
            # 如果用户资料未设置姓名，使用用户名
            form.staff_name.data = current_user.username
    
    # 设置默认公司为"个人"
    form.company_id.data = 0
    
    # 设置默认状态为"进行中"
    form.status.data = 'active'
    
    return render_template('business/projects/project_header/create_header.html', form=form, hid=hid)

@project_create.route('/api/generate-hid')
@login_required
@staff_only
def api_generate_hid():
    """生成项目编号API"""
    try:
        # 直接调用，不需要事务包装
        hid = ProjectHeader.generate_hid()
        
        return jsonify({
            'success': True,
            'data': {'hid': hid}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
