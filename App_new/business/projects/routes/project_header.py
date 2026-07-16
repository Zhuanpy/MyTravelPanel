from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.auth.models.auth import AuthUser, Role, UserProfile
from App_new.exts import csrf, db
from App_new.business.projects.forms.project_forms import ProjectHeaderForm
from App_new.utils.decorators import staff_only, admin_only
from datetime import datetime
from sqlalchemy import func, collate, text
import traceback
import json

# project_invoices.customer_company 与 customer_companies.company_name 的 collation
# 可能不一致 (MySQL 8 常见 utf8mb4_unicode_ci vs utf8mb4_0900_ai_ci),
# 跨字段 / 对比 Python 字符串时显式 COLLATE 统一
_INVOICE_COMPANY_COLLATION = 'utf8mb4_unicode_ci'

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

    # 获取所有公司列表供选择（包含 active 和 inactive，排除 suspended）
    companies = CustomerCompany.query.filter(
        CustomerCompany.status.in_(['active', 'inactive'])
    ).order_by(CustomerCompany.company_name).all()
    
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

    # 处理company_id显示：仅在 GET 请求时将 None 转换为 0 以正确显示"个人"
    # POST 请求时不覆盖用户提交的值
    if request.method == 'GET' and header.company_id is None:
        form.company_id.data = 0  # 显示"个人"

    # 获取第一个REF的描述（用于desc为空时的默认值）
    first_ref = ProjectRef.query.filter_by(header_id=header_id).order_by(ProjectRef.id.asc()).first()
    first_ref_name = first_ref.description if first_ref and first_ref.description else None

    # 获取员工列表（staff和admin角色）
    staff_role = Role.query.filter_by(name='staff').first()
    admin_role = Role.query.filter_by(name='admin').first()
    role_ids = []
    if staff_role:
        role_ids.append(staff_role.id)
    if admin_role:
        role_ids.append(admin_role.id)

    staff_users = []
    if role_ids:
        staff_users = db.session.query(
            AuthUser.id,
            AuthUser.username,
            UserProfile.first_name,
            UserProfile.last_name
        ).outerjoin(
            UserProfile, AuthUser.id == UserProfile.user_id
        ).filter(
            AuthUser.role_id.in_(role_ids),
            AuthUser.is_active == True
        ).all()

    # 转换为列表格式
    staff_list = []
    for user in staff_users:
        # 优先使用profile中的姓名，否则使用username
        if user.first_name or user.last_name:
            display_name = f"{user.first_name or ''}{user.last_name or ''}".strip()
        else:
            display_name = user.username
        staff_list.append({
            'id': user.id,
            'name': display_name,
            'username': user.username
        })

    if request.method == 'POST':
        try:
            # 处理company_id字段，将0转换为None
            if form.company_id.data == 0:
                header.company_id = None
            else:
                header.company_id = form.company_id.data

            # 更新其他字段
            header.hid = form.hid.data

            # 处理desc字段：如果为空则使用第一个REF的描述
            desc_value = form.desc.data
            if not desc_value or desc_value.strip() == '' or desc_value.strip() == '-':
                desc_value = first_ref_name or ''
            header.desc = desc_value

            header.limit = form.limit.data
            header.contact = form.contact.data
            header.dept = form.dept.data
            header.staff_id = form.staff_id.data if form.staff_id.data else None
            # staff_name 由模型事件自动同步
            # 如果负责人姓名为空，自动使用经办人姓名
            header.leader_name = form.leader_name.data if form.leader_name.data else header.staff_name
            header.currency = form.currency.data
            header.type = form.type.data
            header.status = form.status.data
            header.remarks = form.remarks.data

            # 处理操作员和业务员多选
            operator_ids = request.form.getlist('operator_ids')
            salesperson_ids = request.form.getlist('salesperson_ids')

            # 构建ID和姓名字符串
            if operator_ids:
                header.operator_ids = ','.join(operator_ids)
                # 获取对应的姓名
                op_names = []
                for op_id in operator_ids:
                    for s in staff_list:
                        if str(s['id']) == op_id:
                            op_names.append(s['name'])
                            break
                header.operator_names = ','.join(op_names)
            else:
                # 如果没有选择操作员ID，保留原有的姓名（可能是手动输入的）
                # 只有当原来也没有姓名时才清空
                if not header.operator_names:
                    header.operator_ids = None
                    header.operator_names = None

            if salesperson_ids:
                header.salesperson_ids = ','.join(salesperson_ids)
                # 获取对应的姓名
                sp_names = []
                for sp_id in salesperson_ids:
                    for s in staff_list:
                        if str(s['id']) == sp_id:
                            sp_names.append(s['name'])
                            break
                header.salesperson_names = ','.join(sp_names)
            else:
                # 如果没有选择业务员ID，保留原有的姓名（可能是手动输入的）
                # 只有当原来也没有姓名时才清空
                if not header.salesperson_names:
                    header.salesperson_ids = None
                    header.salesperson_names = None

            db.session.commit()

            return redirect(url_for('business_projects.detail.project_detail', project_id=header.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')

    # 获取当前选中的操作员和业务员ID列表
    selected_operator_ids = header.operator_ids.split(',') if header.operator_ids else []
    selected_salesperson_ids = header.salesperson_ids.split(',') if header.salesperson_ids else []

    return render_template('business/projects/project_header/create_header.html',
                         form=form,
                         header=header,
                         hid=header.hid,
                         is_edit=True,
                         first_ref_name=first_ref_name,
                         staff_list=staff_list,
                         selected_operator_ids=selected_operator_ids,
                         selected_salesperson_ids=selected_salesperson_ids)

def get_delete_blockers(header_id):
    """返回禁止删除项目的原因列表（空列表 = 可以删除）

    只要项目还有生效中的业务数据（EO / 发票 / 收款 / 预付款使用 / 退款），
    就不允许删除，避免误删已进入财务流程的项目。
    已作废的记录（EO void / 发票收款退款 cancelled / 预付使用 reversed）不算阻止，
    这样「void 收款 → void 发票 → void EO → 删 REF」走完一圈后项目可以正常删除。
    """
    checks = [
        ('EO', "SELECT COUNT(*) FROM project_eos e "
               "JOIN project_refs r ON e.ref_id = r.id "
               "WHERE r.header_id = :h AND e.status <> 'void'"),
        ('发票', "SELECT COUNT(*) FROM project_invoices "
                 "WHERE header_id = :h AND status <> 'cancelled'"),
        ('收款', "SELECT COUNT(*) FROM project_receipts "
                 "WHERE header_id = :h AND status <> 'cancelled'"),
        ('预付款使用记录',
         "SELECT COUNT(*) FROM prepayment_usages pu "
         "JOIN project_refs r ON pu.ref_id = r.id "
         "WHERE r.header_id = :h AND pu.status <> 'reversed'"),
        ('退款', "SELECT COUNT(*) FROM project_refunds "
                 "WHERE header_id = :h AND status <> 'cancelled'"),
    ]
    blockers = []
    for label, sql in checks:
        count = db.session.execute(text(sql), {'h': header_id}).scalar() or 0
        if count:
            blockers.append(f'{label}（{count} 条）')
    return blockers


@project_header.route('/<int:header_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_header(header_id):
    """删除项目主表（幂等设计：不存在也视为删除成功）

    删除前先判断项目是否已有 EO / 发票 / 收款 / 预付款 / 退款 等业务数据，
    有则拒绝删除；仅对无这些财务动作的项目执行删除。
    """
    try:
        header = ProjectHeader.query.get(header_id)

        if not header:
            # 已被删除或不存在，按成功返回，避免前端出现404提示
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '项目不存在或已删除'})
            else:
                flash('项目不存在或已删除', 'success')
                return redirect(url_for('business_projects.list.list_projects'))

        # 删除前置校验：已有实质业务数据的项目不允许删除
        blockers = get_delete_blockers(header_id)
        if blockers:
            msg = '该项目已有 ' + '、'.join(blockers) + '，不可删除'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': msg})
            else:
                flash(msg, 'error')
                return redirect(url_for('business_projects.detail.project_detail', project_id=header_id))

        # 收集本项目关联的所有 ref / eo / invoice / receipt 主键
        # （数据库里大量子表外键是 ON DELETE NO ACTION，不会随父行级联删除，
        #   必须在删除父行之前按依赖顺序显式清理，否则报 1451 外键约束错误）
        ref_ids = [r[0] for r in db.session.execute(
            text('SELECT id FROM project_refs WHERE header_id = :h'), {'h': header_id})]
        eo_ids = []
        invoice_ids = [r[0] for r in db.session.execute(
            text('SELECT id FROM project_invoices WHERE header_id = :h'), {'h': header_id})]
        receipt_ids = [r[0] for r in db.session.execute(
            text('SELECT id FROM project_receipts WHERE header_id = :h'), {'h': header_id})]

        def _in(ids):
            """把整数主键列表拼成安全的 IN (...) 片段；ids 全部来自数据库主键"""
            return '(' + ','.join(str(int(i)) for i in ids) + ')'

        if ref_ids:
            eo_ids = [r[0] for r in db.session.execute(
                text(f'SELECT id FROM project_eos WHERE ref_id IN {_in(ref_ids)}'))]

        # 依赖顺序：先删最深的子表，逐级向上，最后删主表
        # 每条 DELETE 只在对应 id 列表非空时执行
        stmts = []
        if ref_ids:
            r = _in(ref_ids)
            # 机票：乘客×航段格子(4级) → 乘客/航段(3级) → 订单项
            stmts.append(f'DELETE FROM project_flight_passenger_segments WHERE ref_id IN {r}')
            stmts.append(f'DELETE FROM project_flight_passengers WHERE ref_id IN {r}')
            stmts.append(f'DELETE FROM project_flight_segments WHERE ref_id IN {r}')
            stmts.append(f'DELETE FROM ref_order_items WHERE ref_id IN {r}')
            stmts.append(f'DELETE FROM prepayment_usages WHERE ref_id IN {r}')
            stmts.append(f'DELETE FROM visa_projects WHERE ref_id IN {r}')
        if eo_ids:
            e = _in(eo_ids)
            stmts.append(f'DELETE FROM prepayment_usages WHERE eo_id IN {e}')
            stmts.append(f'DELETE FROM supplier_statement_items WHERE eo_id IN {e}')
        if receipt_ids:
            # 银行流水对收款是 NO ACTION，删收款前先解除匹配
            stmts.append(
                f'UPDATE bank_transactions SET matched_receipt_id = NULL '
                f'WHERE matched_receipt_id IN {_in(receipt_ids)}')
        if invoice_ids:
            # 退款明细引用发票是 NO ACTION，删发票前先删退款明细
            stmts.append(f'DELETE FROM project_refund_items WHERE invoice_id IN {_in(invoice_ids)}')
        # 项目级 NO ACTION 子表
        stmts.append('DELETE FROM project_journal_entries WHERE header_id = :h')
        stmts.append('DELETE FROM project_refunds WHERE header_id = :h')
        stmts.append('DELETE FROM visa_projects WHERE header_id = :h')
        stmts.append('DELETE FROM project_receipts WHERE header_id = :h')
        stmts.append('DELETE FROM project_invoices WHERE header_id = :h')
        if ref_ids:
            stmts.append(f'DELETE FROM project_eos WHERE ref_id IN {_in(ref_ids)}')
        stmts.append('DELETE FROM project_refs WHERE header_id = :h')

        for sql in stmts:
            db.session.execute(text(sql), {'h': header_id})

        # 删除项目主表（project_members / reminders / emails / files 等为 CASCADE，随主表自动删除）
        db.session.execute(text('DELETE FROM project_headers WHERE id = :h'), {'h': header_id})
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
    """更新项目公司

    当公司发生变化时，检查该项目下 confirmed + unpaid 且
    customer_company 快照与新公司名不一致的发票数量，
    在响应中返回 unsynced_invoices 信息供前端弹窗确认是否同步抬头。
    """
    from App_new.business.projects.models.invoice import ProjectInvoice

    data = request.get_json()
    print(f"DEBUG update_company: 收到数据 {data}")

    header_id = data.get('header_id')
    # 兼容两种参数名
    company_id = data.get('company_id') or data.get('company')

    if not header_id:
        return jsonify({'success': False, 'message': '参数错误: header_id为空'})

    # 转换为整数
    header_id = int(header_id)

    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': f'项目不存在: header_id={header_id}'})

    # 处理company_id
    old_company_id = header.company_id
    if company_id is None or company_id == 0 or company_id == '':
        new_company_id = None
    else:
        new_company_id = int(company_id)

    print(f"DEBUG update_company: header_id={header_id}, old={old_company_id}, new={new_company_id}")

    # 直接更新数据库
    try:
        ProjectHeader.query.filter_by(id=header_id).update({'company_id': new_company_id})
        db.session.commit()
        print(f"DEBUG update_company: 提交成功, company_id={new_company_id}")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG update_company: 提交失败 - {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

    # 公司确实发生变化时，统计抬头快照与新公司不一致的未付款发票
    unsynced = {'count': 0, 'new_company_name': None, 'invoice_numbers': []}
    if old_company_id != new_company_id:
        new_company_name = None
        if new_company_id:
            new_company = CustomerCompany.query.get(new_company_id)
            new_company_name = new_company.company_name if new_company else None

        if new_company_name:
            mismatched = ProjectInvoice.query.filter(
                ProjectInvoice.header_id == header_id,
                ProjectInvoice.status == 'confirmed',
                ProjectInvoice.payment_status != 'paid',
                db.or_(
                    ProjectInvoice.customer_company.is_(None),
                    ProjectInvoice.customer_company != collate(db.literal(new_company_name), _INVOICE_COMPANY_COLLATION)
                )
            ).all()

            unsynced['count'] = len(mismatched)
            unsynced['new_company_name'] = new_company_name
            unsynced['invoice_numbers'] = [inv.invoice_number for inv in mismatched[:10]]

    return jsonify({
        'success': True,
        'company_id': new_company_id,
        'unsynced_invoices': unsynced
    })


@project_header.route('/sync_invoice_company', methods=['POST'])
@csrf.exempt
def sync_invoice_customer_company():
    """将项目下 confirmed + unpaid 的发票 customer_company 同步为项目当前公司名"""
    from App_new.business.projects.models.invoice import ProjectInvoice

    data = request.get_json() or {}
    header_id = data.get('header_id')
    if not header_id:
        return jsonify({'success': False, 'message': '参数错误: header_id为空'})

    header_id = int(header_id)
    header = ProjectHeader.query.get(header_id)
    if not header:
        return jsonify({'success': False, 'message': f'项目不存在: header_id={header_id}'})

    new_company_name = header.company.company_name if header.company else None
    if not new_company_name:
        return jsonify({'success': False, 'message': '项目当前未关联公司，无法同步'})

    try:
        result = ProjectInvoice.query.filter(
            ProjectInvoice.header_id == header_id,
            ProjectInvoice.status == 'confirmed',
            ProjectInvoice.payment_status != 'paid',
            db.or_(
                ProjectInvoice.customer_company.is_(None),
                ProjectInvoice.customer_company != collate(db.literal(new_company_name), _INVOICE_COMPANY_COLLATION)
            )
        ).update(
            {'customer_company': new_company_name},
            synchronize_session=False
        )
        db.session.commit()
        return jsonify({
            'success': True,
            'updated': int(result or 0),
            'customer_company': new_company_name
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

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
    valid_statuses = ['active', 'completed', 'cancelled']
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



