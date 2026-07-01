from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.projects.models.project import CustomerCompany, CompanyContact, CompanyFile
from werkzeug.utils import secure_filename
import uuid
from App_new.shared.forms.company_forms import CustomerCompanyForm
from App_new.utils.decorators import staff_only
from sqlalchemy import or_
import pandas as pd
import io
import os
from datetime import datetime

corporate = Blueprint('corporate', __name__)

from App_new.auth.models.auth import AuthUser, Role, UserProfile


def _get_staff_list():
    """员工列表（staff + admin 角色，启用中），用于客户归属选择。"""
    role_ids = [r.id for r in Role.query.filter(Role.name.in_(['staff', 'admin'])).all()]
    if not role_ids:
        return []
    rows = db.session.query(
        AuthUser.id, AuthUser.username, UserProfile.first_name, UserProfile.last_name
    ).outerjoin(UserProfile, AuthUser.id == UserProfile.user_id).filter(
        AuthUser.role_id.in_(role_ids), AuthUser.is_active == True
    ).all()
    result = []
    for r in rows:
        name = f"{r.first_name or ''}{r.last_name or ''}".strip() or r.username
        result.append({'id': r.id, 'name': name})
    result.sort(key=lambda x: x['name'])
    return result


def _current_staff_level():
    """当前用户员工等级；非 staff 角色（管理员等）视为最高级，可见全部。"""
    if not (current_user.is_authenticated and current_user.role and current_user.role.name == 'staff'):
        return 99
    if current_user.profile:
        return current_user.profile.staff_level or 1
    return 1


def _can_access_company(company):
    """是否有权访问/编辑该客户：无归属(共享) / 归属本人 / 2级及以上。"""
    if company.staff_id is None:
        return True
    if _current_staff_level() >= 2:
        return True
    return company.staff_id == current_user.id


@corporate.route('/')
@login_required
@staff_only
def list_companies():
    """公司列表（支持客户/供应商角色筛选）"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    group_name_filter = request.args.get('group_name', '')
    role = request.args.get('role', '')  # customer, supplier, all

    query = CustomerCompany.query

    # 归属过滤：1级员工只能看到自己归属 + 无归属(共享)的客户；2级/管理员看全部
    if _current_staff_level() < 2:
        query = query.filter(
            or_(
                CustomerCompany.staff_id.is_(None),
                CustomerCompany.staff_id == current_user.id
            )
        )

    # 角色筛选
    if role == 'customer':
        query = query.filter(CustomerCompany.is_customer == True)
    elif role == 'supplier':
        query = query.filter(CustomerCompany.is_supplier == True)
    # role == 'all' 或空则显示全部

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

    # 集团/关联标签筛选
    if group_name_filter:
        if group_name_filter == 'has_group':
            query = query.filter(
                CustomerCompany.group_name.isnot(None),
                CustomerCompany.group_name != ''
            )
        elif group_name_filter == 'no_group':
            query = query.filter(
                or_(
                    CustomerCompany.group_name.is_(None),
                    CustomerCompany.group_name == ''
                )
            )
        else:
            query = query.filter(CustomerCompany.group_name == group_name_filter)

    # 按点击次数降序排列，点击次数相同时按创建时间降序排列
    companies = query.order_by(
        CustomerCompany.click_count.desc(),
        CustomerCompany.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    # 获取所有已使用的集团/关联标签，用于筛选下拉列表
    group_names = get_existing_group_names()

    # 获取供应商类型列表（用于筛选）
    from App_new.shared.models.business_types import BusinessType
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    return render_template('shared/corporate/corporate_list.html',
                           companies=companies,
                           group_names=group_names,
                           supplier_types=supplier_types,
                           current_role=role)


# 客户归属：无权访问时的统一处理
def _deny_company_access():
    flash('无权访问该客户（该客户归属其他员工）', 'error')
    return redirect(url_for('corporate.list_companies'))

@corporate.route('/api/click/<int:company_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def record_company_click(company_id):
    """记录公司点击次数"""
    try:
        company = CustomerCompany.query.get_or_404(company_id)
        company.increment_click_count()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'click_count': company.click_count,
            'last_clicked_at': company.last_clicked_at.isoformat() if company.last_clicked_at else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_existing_group_names():
    """获取已有的集团/关联标签列表（用于自动补全）"""
    result = db.session.query(CustomerCompany.group_name).filter(
        CustomerCompany.group_name.isnot(None),
        CustomerCompany.group_name != ''
    ).distinct().order_by(CustomerCompany.group_name).all()
    return [r[0] for r in result]

@corporate.route('/create', methods=['GET', 'POST'])
@login_required
@staff_only
def create_company():
    """创建公司（客户/供应商）"""
    form = CustomerCompanyForm()

    # 获取供应商类型列表
    from App_new.shared.models.business_types import BusinessType
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    if form.validate_on_submit():
        try:
            # 设置创建时间：如果表单中有值则使用表单值，否则使用当前时间
            created_at = form.created_at.data if form.created_at.data else datetime.utcnow()

            # 处理集团/关联标签（自动转大写）
            group_name = form.group_name.data.strip().upper() if form.group_name.data else None

            # 获取角色标识
            is_customer = request.form.get('is_customer') == 'on'
            is_supplier = request.form.get('is_supplier') == 'on'

            # 至少选择一个角色
            if not is_customer and not is_supplier:
                is_customer = True

            company = CustomerCompany(
                company_name=form.company_name.data.upper() if form.company_name.data else '',
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
                created_at=created_at,
                created_by=current_user.username if current_user.is_authenticated else 'system',
                group_name=group_name,
                # 新增字段
                is_customer=is_customer,
                is_supplier=is_supplier,
                supplier_type_id=request.form.get('supplier_type_id', type=int) or None,
                country=request.form.get('country', '').strip() or None,
                city=request.form.get('city', '').strip() or None,
                region=request.form.get('region', '').strip() or None,
                # 所属员工（归属）
                staff_id=request.form.get('staff_id', type=int) or None
            )
            db.session.add(company)
            db.session.commit()
            flash('公司创建成功！', 'success')
            return redirect(url_for('corporate.list_companies'))
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)

            # 检查是否是重复公司名称错误
            if "Duplicate entry" in error_msg and "company_name" in error_msg:
                company_name = form.company_name.data
                flash(f'创建失败：公司名称 "{company_name}" 已存在，请使用其他名称', 'error')
            else:
                flash(f'创建失败：{error_msg}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')

    return render_template('shared/corporate/corporate_form.html',
                           form=form,
                           company=None,
                           existing_group_names=get_existing_group_names(),
                           supplier_types=supplier_types,
                           staff_list=_get_staff_list())

@corporate.route('/<int:company_id>')
@login_required
@staff_only
def company_detail(company_id):
    """客户公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    if not _can_access_company(company):
        return _deny_company_access()

    # 查询预付账款信息（只要有数据就显示）
    prepayment_stats = None
    prepayment_records = []

    from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment

    # 查询该公司的所有已确认预付记录
    prepayments = SupplierPrepayment.query.filter(
        SupplierPrepayment.supplier_id == company_id,
        SupplierPrepayment.status.in_(['confirmed', 'partial_used', 'consumed'])
    ).all()

    # 如果有预付数据，计算统计
    if prepayments:
        total_recharged = sum(float(p.amount) for p in prepayments)
        total_balance = sum(float(p.balance_amount) for p in prepayments)
        total_used = total_recharged - total_balance

        prepayment_stats = {
            'total_recharged': total_recharged,
            'total_used': total_used,
            'total_balance': total_balance,
            'count': len(prepayments)
        }

        # 获取最近5条预付记录
        prepayment_records = SupplierPrepayment.query.filter(
            SupplierPrepayment.supplier_id == company_id
        ).order_by(SupplierPrepayment.created_at.desc()).limit(5).all()

    # 查询关联账号
    from App_new.shared.models.account import Account
    linked_accounts = Account.query.filter_by(supplier_id=company_id).order_by(Account.platform).all()

    return render_template('shared/corporate/corporate_detail.html',
                           company=company,
                           prepayment_stats=prepayment_stats,
                           prepayment_records=prepayment_records,
                           linked_accounts=linked_accounts)


@corporate.route('/<int:company_id>/initial-balance', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def create_initial_balance(company_id):
    """创建初始余额预付记录"""
    try:
        company = CustomerCompany.query.get_or_404(company_id)
        if not _can_access_company(company):
            return jsonify({'success': False, 'message': '无权操作该客户'}), 403

        data = request.get_json()
        amount = data.get('amount')
        remarks = data.get('remarks', 'Initial Balance')

        if not amount or float(amount) <= 0:
            return jsonify({'success': False, 'message': '金额必须大于0'}), 400

        from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
        from datetime import date

        # 生成预付编号
        prepayment_number = SupplierPrepayment.generate_prepayment_number()

        # 创建预付记录
        prepayment = SupplierPrepayment(
            prepayment_number=prepayment_number,
            supplier_id=company_id,
            amount=float(amount),
            balance_amount=float(amount),  # 初始余额 = 充值金额
            currency='SGD',
            payment_date=date.today(),
            payment_method='other',
            status='confirmed',  # 初始余额直接确认
            remarks=remarks,
            created_by=current_user.username if current_user.is_authenticated else 'system'
        )

        db.session.add(prepayment)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '初始余额设置成功',
            'prepayment_id': prepayment.id,
            'prepayment_number': prepayment.prepayment_number
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/prepayments')
@login_required
@staff_only
def get_company_prepayments(company_id):
    """获取公司的预付账款列表"""
    try:
        from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment

        # 获取公司信息
        company = CustomerCompany.query.get(company_id)
        if company and not _can_access_company(company):
            return jsonify({'success': False, 'message': '无权访问该客户'}), 403
        supplier_name = company.company_name if company else ''

        # 查询该公司的有效预付记录（按时间升序，用于 FIFO）
        # 注意：用 balance_amount > 0 而非 status 过滤，
        # 防止历史脏数据（status='consumed' 但余额因冲销恢复 > 0）导致漏算
        prepayments = SupplierPrepayment.query.filter(
            SupplierPrepayment.supplier_id == company_id,
            SupplierPrepayment.balance_amount > 0,
            SupplierPrepayment.status != 'cancelled',
            SupplierPrepayment.status != 'draft'
        ).order_by(SupplierPrepayment.created_at.asc()).all()

        # 直接使用 balance_amount 字段计算可用余额
        # 注意：不能只统计 confirmed 使用记录，因为 pending 状态的记录也已实际扣减了 balance_amount
        total_available = 0
        result_prepayments = []
        for p in prepayments:
            available = float(p.balance_amount)
            if available > 0:
                p_dict = p.to_dict()
                p_dict['available_balance'] = available
                result_prepayments.append(p_dict)
                total_available += available

        # 如果传入了eo_ids，计算已有的pending/confirmed使用记录总额
        # 这些EO已经扣了balance_amount，批量付款时不需要重复扣减
        existing_usage_total = 0
        eo_ids_str = request.args.get('eo_ids', '')
        if eo_ids_str:
            try:
                from App_new.business.projects.models.supplier_prepayment import PrepaymentUsage
                eo_ids = [int(x) for x in eo_ids_str.split(',') if x.strip()]
                if eo_ids:
                    from sqlalchemy import func
                    usage_sum = db.session.query(func.sum(PrepaymentUsage.amount)).filter(
                        PrepaymentUsage.eo_id.in_(eo_ids),
                        PrepaymentUsage.status.in_(['pending', 'confirmed'])
                    ).scalar()
                    existing_usage_total = float(usage_sum) if usage_sum else 0
            except (ValueError, TypeError):
                pass

        return jsonify({
            'success': True,
            'prepayments': result_prepayments,
            'supplier_name': supplier_name,
            'total_balance': total_available,
            'existing_usage_total': existing_usage_total
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_only
def edit_company(company_id):
    """编辑公司（客户/供应商）"""
    company = CustomerCompany.query.get_or_404(company_id)
    if not _can_access_company(company):
        return _deny_company_access()
    form = CustomerCompanyForm(obj=company)

    # 获取供应商类型列表
    from App_new.shared.models.business_types import BusinessType
    supplier_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    if form.validate_on_submit():
        try:
            form.populate_obj(company)
            # 确保公司名称为大写
            if company.company_name:
                company.company_name = company.company_name.upper()

            # 处理集团/关联标签（自动转大写）
            if company.group_name:
                company.group_name = company.group_name.strip().upper()

            # 如果没有设置创建时间，自动设置为今天
            if not company.created_at:
                company.created_at = datetime.utcnow()

            # 更新角色标识
            company.is_customer = request.form.get('is_customer') == 'on'
            company.is_supplier = request.form.get('is_supplier') == 'on'

            # 至少选择一个角色
            if not company.is_customer and not company.is_supplier:
                company.is_customer = True

            # 更新供应商专属字段
            company.supplier_type_id = request.form.get('supplier_type_id', type=int) or None
            company.country = request.form.get('country', '').strip() or None
            company.city = request.form.get('city', '').strip() or None
            company.region = request.form.get('region', '').strip() or None
            # 所属员工（归属）
            company.staff_id = request.form.get('staff_id', type=int) or None

            db.session.commit()
            return redirect(url_for('corporate.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')

    return render_template('shared/corporate/corporate_form.html',
                           form=form,
                           company=company,
                           existing_group_names=get_existing_group_names(),
                           supplier_types=supplier_types,
                           staff_list=_get_staff_list())

@corporate.route('/<int:company_id>/delete', methods=['POST'])
@login_required
@staff_only
def delete_company(company_id):
    """删除客户公司"""
    company = CustomerCompany.query.get_or_404(company_id)
    if not _can_access_company(company):
        return _deny_company_access()
    try:
        db.session.delete(company)
        db.session.commit()
        flash('公司删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('corporate.list_companies'))

@corporate.route('/api/search')
@login_required
@staff_only
def api_search_companies():
    """API搜索公司（用于下拉选择 / 自动化按名称或代码查ID）

    按 company_name 或 company_code 模糊匹配；每条附主要联系人（is_primary），
    供自动化下单直接拿到公司ID + 默认联系人。备选联系人用 /api/<id>/contacts。
    """
    search = request.args.get('q', '').strip()
    query = CustomerCompany.query
    if search:
        # 分词 AND 匹配：每个词都需命中 company_name 或 company_code（顺序无关），
        # 这样 "TENG XUAN" 也能匹配 "XUAN TENG CONSTRUCTION"，多词/隔词更宽容。
        for term in search.split():
            like = f'%{term}%'
            query = query.filter(or_(
                CustomerCompany.company_name.ilike(like),
                CustomerCompany.company_code.ilike(like),
                CustomerCompany.alias.ilike(like)
            ))
    companies = query.limit(10).all()

    def _primary_contact(c):
        contact = c.contacts.filter_by(is_primary=True).first() or c.contacts.first()
        return contact.name if contact else (c.contact_person or None)

    return jsonify([{
        'id': company.id,
        'text': company.company_name,
        'company_name': company.company_name,
        'company_code': company.company_code,
        'alias': company.alias,
        'primary_contact': _primary_contact(company),
        'contact_person': company.contact_person,
        'contact_phone': company.contact_phone
    } for company in companies])

@corporate.route('/api/search-group')
@login_required
@staff_only
def api_search_group_companies():
    """API搜索集团/关联公司（用于Select2下拉选择）"""
    search = request.args.get('q', '')
    exclude_id = request.args.get('exclude_id', '')
    
    query = CustomerCompany.query.filter(CustomerCompany.status == 'active')
    
    if search:
        query = query.filter(CustomerCompany.company_name.ilike(f'%{search}%'))
    
    # 排除当前编辑的公司（避免自引用）
    if exclude_id:
        try:
            query = query.filter(CustomerCompany.id != int(exclude_id))
        except ValueError:
            pass
    
    companies = query.order_by(CustomerCompany.company_name).limit(20).all()
    
    return jsonify([{
        'id': company.id,
        'company_name': company.company_name
    } for company in companies])

@corporate.route('/api/<int:company_id>')
@login_required
@staff_only
def api_company_detail(company_id):
    """API获取公司详情"""
    company = CustomerCompany.query.get_or_404(company_id)
    return jsonify(company.to_dict())

@corporate.route('/api/<int:company_id>/contacts')
@login_required
@staff_only
def api_company_contacts(company_id):
    """API获取公司联系人列表（含 is_primary 主要联系人标记）

    供自动化下单选联系人：默认取 is_primary=True，其余为可选，主要联系人排最前。
    替代爬取公司详情页 HTML（联系人表格为 Vue 动态渲染，HTML 抓不到）。
    """
    company = CustomerCompany.query.get_or_404(company_id)
    contacts = company.contacts.order_by(
        CompanyContact.is_primary.desc(), CompanyContact.id
    ).all()
    return jsonify({
        'success': True,
        'company_id': company.id,
        'company_name': company.company_name,
        'company_code': company.company_code,
        'contacts': [c.to_dict() for c in contacts]
    })

@corporate.route('/download-template')
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

@corporate.route('/import-excel', methods=['POST'])
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
                    company_name=company_data['company_name'].upper(),
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


# ==================== 联系人管理 API ====================

@corporate.route('/<int:company_id>/contacts')
@login_required
@staff_only
def get_contacts(company_id):
    """获取公司联系人列表"""
    company = CustomerCompany.query.get_or_404(company_id)
    contacts = CompanyContact.query.filter_by(company_id=company_id).order_by(
        CompanyContact.is_primary.desc(),
        CompanyContact.created_at.desc()
    ).all()
    return jsonify({
        'success': True,
        'contacts': [c.to_dict() for c in contacts]
    })


@corporate.route('/<int:company_id>/contacts/add', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def add_contact(company_id):
    """添加联系人"""
    try:
        company = CustomerCompany.query.get_or_404(company_id)
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'message': '联系人姓名不能为空'}), 400
        
        contact = CompanyContact(
            company_id=company_id,
            name=data.get('name'),
            position=data.get('position'),
            phone=data.get('phone'),
            email=data.get('email'),
            wechat=data.get('wechat'),
            is_primary=data.get('is_primary', False),
            remarks=data.get('remarks')
        )
        
        # 如果设为主要联系人，取消其他主要联系人
        if contact.is_primary:
            CompanyContact.query.filter_by(company_id=company_id, is_primary=True).update({'is_primary': False})
        
        db.session.add(contact)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '联系人添加成功',
            'contact': contact.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/contacts/<int:contact_id>', methods=['GET'])
@login_required
@staff_only
def get_contact(company_id, contact_id):
    """获取单个联系人"""
    contact = CompanyContact.query.filter_by(id=contact_id, company_id=company_id).first_or_404()
    return jsonify({
        'success': True,
        'contact': contact.to_dict()
    })


@corporate.route('/<int:company_id>/contacts/<int:contact_id>/update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_contact(company_id, contact_id):
    """更新联系人"""
    try:
        contact = CompanyContact.query.filter_by(id=contact_id, company_id=company_id).first_or_404()
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'message': '联系人姓名不能为空'}), 400
        
        contact.name = data.get('name')
        contact.position = data.get('position')
        contact.phone = data.get('phone')
        contact.email = data.get('email')
        contact.wechat = data.get('wechat')
        contact.remarks = data.get('remarks')
        
        # 处理主要联系人
        new_is_primary = data.get('is_primary', False)
        if new_is_primary and not contact.is_primary:
            # 取消其他主要联系人
            CompanyContact.query.filter(
                CompanyContact.company_id == company_id,
                CompanyContact.id != contact_id,
                CompanyContact.is_primary == True
            ).update({'is_primary': False})
        contact.is_primary = new_is_primary
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '联系人更新成功',
            'contact': contact.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/contacts/<int:contact_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_contact(company_id, contact_id):
    """删除联系人"""
    try:
        contact = CompanyContact.query.filter_by(id=contact_id, company_id=company_id).first_or_404()
        db.session.delete(contact)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '联系人删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 公司文件管理 API ====================

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z', 'txt'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_company_files_path(company_id):
    """获取公司文件存储路径"""
    from pathlib import Path
    base_path = Path(os.getcwd()) / '资源' / 'Company' / str(company_id)
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@corporate.route('/<int:company_id>/files')
@login_required
@staff_only
def get_files(company_id):
    """获取公司文件列表"""
    company = CustomerCompany.query.get_or_404(company_id)
    files = CompanyFile.query.filter_by(company_id=company_id).order_by(
        CompanyFile.created_at.desc()
    ).all()
    return jsonify({
        'success': True,
        'files': [f.to_dict() for f in files]
    })


@corporate.route('/<int:company_id>/files/upload', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def upload_file(company_id):
    """上传公司文件"""
    try:
        company = CustomerCompany.query.get_or_404(company_id)

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400

        # 生成安全的文件名
        original_filename = file.filename
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        stored_filename = f"{uuid.uuid4().hex}.{file_ext}"

        # 获取存储路径
        files_path = get_company_files_path(company_id)
        file_path = files_path / stored_filename

        # 保存文件
        file.save(str(file_path))

        # 获取文件大小
        file_size = os.path.getsize(str(file_path))

        # 获取描述（如果有）
        description = request.form.get('description', '')

        # 创建数据库记录
        company_file = CompanyFile(
            company_id=company_id,
            filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file.content_type,
            description=description,
            uploaded_by=current_user.username if current_user.is_authenticated else 'system'
        )

        db.session.add(company_file)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file': company_file.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/files/<int:file_id>/download')
@login_required
@staff_only
def download_file(company_id, file_id):
    """下载公司文件"""
    try:
        company_file = CompanyFile.query.filter_by(id=file_id, company_id=company_id).first_or_404()

        if not os.path.exists(company_file.file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404

        return send_file(
            company_file.file_path,
            as_attachment=True,
            download_name=company_file.filename
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/files/<int:file_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_file(company_id, file_id):
    """删除公司文件"""
    try:
        company_file = CompanyFile.query.filter_by(id=file_id, company_id=company_id).first_or_404()

        # 删除物理文件
        if os.path.exists(company_file.file_path):
            os.remove(company_file.file_path)

        # 删除数据库记录
        db.session.delete(company_file)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/files/<int:file_id>/update', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_file(company_id, file_id):
    """更新文件描述"""
    try:
        company_file = CompanyFile.query.filter_by(id=file_id, company_id=company_id).first_or_404()
        data = request.get_json()

        if 'description' in data:
            company_file.description = data['description']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '更新成功',
            'file': company_file.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 邮件发送 ====================

@corporate.route('/<int:company_id>/email/templates')
@login_required
@staff_only
def get_email_templates(company_id):
    """获取可用的邮件模板列表"""
    try:
        from App_new.business.projects.models.project import EmailTemplate
        templates = EmailTemplate.query.filter_by(is_active=True).order_by(
            EmailTemplate.category, EmailTemplate.name
        ).all()
        return jsonify({
            'success': True,
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@corporate.route('/<int:company_id>/email/send', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def send_company_email(company_id):
    """发送邮件给公司联系人（支持附件）"""
    try:
        from flask import current_app
        from flask_mail import Mail, Message
        import logging
        import re
        import mimetypes

        logger = logging.getLogger(__name__)
        company = CustomerCompany.query.get_or_404(company_id)

        # 支持 FormData（含附件）和 JSON 两种格式
        if request.content_type and 'multipart/form-data' in request.content_type:
            recipients_str = request.form.get('recipient', '').strip()
            cc_str = request.form.get('cc', '').strip()
            subject = request.form.get('subject', '').strip()
            body = request.form.get('body', '').strip()
            files = request.files.getlist('attachments')
        else:
            data = request.get_json()
            recipients_str = data.get('recipient', '').strip()
            cc_str = data.get('cc', '').strip()
            subject = data.get('subject', '').strip()
            body = data.get('body', '').strip()
            files = []

        if not recipients_str:
            return jsonify({'success': False, 'message': '请填写收件人邮箱'}), 400
        if not subject:
            return jsonify({'success': False, 'message': '请填写邮件主题'}), 400
        if not body:
            return jsonify({'success': False, 'message': '请填写邮件内容'}), 400

        # 解析收件人（支持逗号/分号分隔）
        recipients = [e.strip() for e in re.split(r'[,;，；]', recipients_str) if e.strip()]
        cc = [e.strip() for e in re.split(r'[,;，；]', cc_str) if e.strip()] if cc_str else []

        # 检查邮件配置
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')

        if not mail_server or not mail_username or not mail_password:
            return jsonify({'success': False, 'message': '邮件服务器未配置，请联系管理员'}), 500

        # 发送邮件
        mail = Mail(current_app)
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or mail_username

        # 正文：富文本编辑器已是 HTML 则直接用，纯文本则转义并换行
        has_html_tags = '<' in body and '>' in body and any(
            tag in body.lower() for tag in ['<br', '<p', '<div', '<span', '<h', '<strong', '<em', '<u', '<ol', '<ul', '<a', '<b>', '<i>']
        )
        if has_html_tags:
            html_body = body
        else:
            import html as html_module
            escaped_body = html_module.escape(body)
            html_body = escaped_body.replace('\n', '<br>')
            html_body = f'<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">{html_body}</div>'

        msg = Message(
            subject=subject,
            sender=sender_email,
            recipients=recipients,
            cc=cc if cc else None,
            html=html_body
        )

        # 添加附件
        att_count = 0
        for f in files:
            if f and f.filename:
                mime_type, _ = mimetypes.guess_type(f.filename)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                msg.attach(f.filename, mime_type, f.read())
                att_count += 1

        logger.info(f"公司邮件发送 - 公司: {company.company_name}, 收件人: {recipients}, 附件: {att_count}")
        mail.send(msg)
        logger.info("公司邮件发送成功")

        result_msg = f'邮件已发送至 {", ".join(recipients)}'
        if att_count:
            result_msg += f'，包含 {att_count} 个附件'

        return jsonify({'success': True, 'message': result_msg})

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"公司邮件发送失败: {str(e)}")
        return jsonify({'success': False, 'message': f'发送失败: {str(e)}'}), 500
