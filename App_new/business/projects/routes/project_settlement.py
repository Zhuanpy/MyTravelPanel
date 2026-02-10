# -*- coding: utf-8 -*-
"""
项目结算路由
包含项目结算页面、批量结算等功能
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO
from App_new.business.projects.models.invoice import InvoiceItem
from App_new.utils.decorators import staff_only
from datetime import datetime
import traceback
import pandas as pd
from io import BytesIO


# 创建蓝图
bp = Blueprint('settlement', __name__)


@bp.route('/')
@login_required
@staff_only
def settlement_list():
    """项目结算列表页面"""
    try:
        # 获取筛选参数
        search = request.args.get('search', '')
        staff_id = request.args.get('staff_id', '', type=int) if request.args.get('staff_id') else ''
        settlement_status = request.args.get('settlement_status', '')
        profit_status = request.args.get('profit_status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = request.args.get('page', 1, type=int)
        per_page = 30

        # 构建查询
        base_query = ProjectHeader.query.options(
            db.joinedload(ProjectHeader.company)
        )

        # 应用搜索
        if search:
            base_query = base_query.outerjoin(CustomerCompany).filter(
                db.or_(
                    ProjectHeader.hid.like(f'%{search}%'),
                    CustomerCompany.company_name.like(f'%{search}%')
                )
            )

        # 经办人筛选
        if staff_id:
            base_query = base_query.filter(ProjectHeader.staff_id == staff_id)

        # 日期筛选
        if date_from:
            base_query = base_query.filter(ProjectHeader.created_at >= date_from)
        if date_to:
            base_query = base_query.filter(ProjectHeader.created_at <= date_to + ' 23:59:59')

        # 结算状态筛选
        if settlement_status:
            if settlement_status == 'settled':
                base_query = base_query.filter(ProjectHeader.is_settled == True)
            elif settlement_status == 'unsettled':
                base_query = base_query.filter(ProjectHeader.is_settled == False)
            elif settlement_status == 'can_settle':
                # 可结算：构建复杂子查询
                base_query = base_query.filter(ProjectHeader.is_settled == False)
                base_query = _apply_can_settle_filter(base_query)

        # 盈亏状态筛选
        if profit_status:
            profit_subquery = db.session.query(ProjectRef.header_id).group_by(ProjectRef.header_id)
            if profit_status == 'profit':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) > 0
                )
            elif profit_status == 'loss':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) < 0
                )
            elif profit_status == 'zero':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) == 0
                )
            base_query = base_query.filter(ProjectHeader.id.in_(profit_subquery))

        # 排序
        base_query = base_query.order_by(ProjectHeader.created_at.desc())

        # 分页
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
        projects = pagination.items

        # 获取项目统计信息（当前页）
        project_ids = [p.id for p in projects]
        project_stats = _get_project_stats(project_ids)

        # 获取筛选后的全部项目ID（用于计算筛选后的汇总统计）
        all_filtered_ids = [p.id for p in base_query.with_entities(ProjectHeader.id).all()]
        all_filtered_stats = _get_project_stats(all_filtered_ids) if all_filtered_ids else {}

        # 计算统计数据（基于筛选后的全部数据）
        stats = _calculate_stats(all_filtered_stats, base_query)

        # 获取经办人列表（从员工表获取）
        from App_new.auth.models.auth import AuthUser, Role, UserProfile
        staff_role = Role.query.filter_by(name='staff').first()
        admin_role = Role.query.filter_by(name='admin').first()
        role_ids = []
        if staff_role:
            role_ids.append(staff_role.id)
        if admin_role:
            role_ids.append(admin_role.id)

        staff_list = []
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
            for u in staff_users:
                if u.first_name or u.last_name:
                    display_name = f"{u.first_name or ''}{u.last_name or ''}".strip()
                else:
                    display_name = u.username
                staff_list.append({'id': u.id, 'name': display_name})

        # 构建操作员/业务员名字映射（从员工表获取）
        staff_name_map = {s['id']: s['name'] for s in staff_list}
        project_staff_display = {}
        for p in projects:
            op_ids = [int(s.strip()) for s in (p.operator_ids or '').split(',') if s.strip() and s.strip().isdigit()]
            sp_ids = [int(s.strip()) for s in (p.salesperson_ids or '').split(',') if s.strip() and s.strip().isdigit()]
            project_staff_display[p.id] = {
                'operator_names': ', '.join(staff_name_map.get(uid, f'ID:{uid}') for uid in op_ids) if op_ids else (p.operator_names or '-'),
                'salesperson_names': ', '.join(staff_name_map.get(uid, f'ID:{uid}') for uid in sp_ids) if sp_ids else (p.salesperson_names or '-'),
            }

        # 构建查询字符串用于分页
        query_params = []
        if search:
            query_params.append(f'search={search}')
        if staff_id:
            query_params.append(f'staff_id={staff_id}')
        if settlement_status:
            query_params.append(f'settlement_status={settlement_status}')
        if profit_status:
            query_params.append(f'profit_status={profit_status}')
        if date_from:
            query_params.append(f'date_from={date_from}')
        if date_to:
            query_params.append(f'date_to={date_to}')
        query_string = '&'.join(query_params)

        return render_template(
            'business/projects/project_settlement.html',
            projects=projects,
            project_stats=project_stats,
            pagination=pagination,
            stats=stats,
            staff_list=staff_list,
            project_staff_display=project_staff_display,
            query_string=query_string,
            filters={
                'search': search,
                'staff_id': staff_id,
                'settlement_status': settlement_status,
                'profit_status': profit_status,
                'date_from': date_from,
                'date_to': date_to
            }
        )

    except Exception as e:
        traceback.print_exc()
        return render_template(
            'business/projects/project_settlement.html',
            projects=[],
            project_stats={},
            pagination=None,
            stats={'can_settle_count': 0, 'settled_count': 0, 'unsettled_count': 0,
                   'page_total_profit': 0, 'page_total_selling': 0, 'page_total_cost': 0,
                   'page_total_received': 0, 'page_total_balance': 0},
            staff_list=[],
            query_string='',
            filters={}
        )


def _apply_can_settle_filter(base_query):
    """应用可结算筛选条件"""
    # REF总数子查询
    ref_count_subq = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectRef.id).label('ref_count')
    ).group_by(ProjectRef.header_id).subquery()

    # 有发票的REF数量子查询
    invoiced_ref_subq = db.session.query(
        ProjectRef.header_id,
        db.func.count(db.distinct(InvoiceItem.ref_id)).label('invoiced_count')
    ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id
    ).group_by(ProjectRef.header_id).subquery()

    # EO总数子查询
    eo_count_subq = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectEO.id).label('eo_count')
    ).join(ProjectEO, ProjectEO.ref_id == ProjectRef.id
    ).group_by(ProjectRef.header_id).subquery()

    # 已付款EO数量子查询（is_paid == True 视为已付款）
    paid_eo_subq = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectEO.id).label('paid_count')
    ).join(ProjectEO, ProjectEO.ref_id == ProjectRef.id
    ).filter(ProjectEO.is_paid == True
    ).group_by(ProjectRef.header_id).subquery()

    # 销售总额子查询
    selling_subq = db.session.query(
        ProjectRef.header_id,
        db.func.coalesce(db.func.sum(ProjectRef.selling_price), 0).label('total_selling')
    ).group_by(ProjectRef.header_id).subquery()

    # 收款总额子查询
    receipt_subq = db.session.query(
        ProjectReceipt.header_id,
        db.func.coalesce(db.func.sum(ProjectReceipt.amount), 0).label('total_received')
    ).filter(ProjectReceipt.status == 'confirmed'
    ).group_by(ProjectReceipt.header_id).subquery()

    # 组合查询
    can_settle_subq = db.session.query(ref_count_subq.c.header_id).outerjoin(
        invoiced_ref_subq, invoiced_ref_subq.c.header_id == ref_count_subq.c.header_id
    ).outerjoin(
        eo_count_subq, eo_count_subq.c.header_id == ref_count_subq.c.header_id
    ).outerjoin(
        paid_eo_subq, paid_eo_subq.c.header_id == ref_count_subq.c.header_id
    ).outerjoin(
        selling_subq, selling_subq.c.header_id == ref_count_subq.c.header_id
    ).outerjoin(
        receipt_subq, receipt_subq.c.header_id == ref_count_subq.c.header_id
    ).filter(
        ref_count_subq.c.ref_count > 0,
        ref_count_subq.c.ref_count == db.func.coalesce(invoiced_ref_subq.c.invoiced_count, 0),
        db.or_(
            eo_count_subq.c.eo_count.is_(None),
            eo_count_subq.c.eo_count == db.func.coalesce(paid_eo_subq.c.paid_count, 0)
        ),
        db.func.abs(
            db.func.coalesce(selling_subq.c.total_selling, 0) -
            db.func.coalesce(receipt_subq.c.total_received, 0)
        ) < 0.01
    )

    return base_query.filter(ProjectHeader.id.in_(can_settle_subq))


def _get_project_stats(project_ids):
    """获取项目统计信息"""
    if not project_ids:
        return {}

    project_stats = {}

    # 批量查询REF数据
    refs_data = db.session.query(
        ProjectRef.header_id,
        db.func.sum(ProjectRef.selling_price).label('total_selling'),
        db.func.sum(ProjectRef.cost_price).label('total_cost')
    ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()

    # 批量查询收款数据
    receipts_data = db.session.query(
        ProjectReceipt.header_id,
        db.func.sum(ProjectReceipt.amount).label('total_received')
    ).filter(
        ProjectReceipt.header_id.in_(project_ids),
        ProjectReceipt.status == 'confirmed'
    ).group_by(ProjectReceipt.header_id).all()
    receipts_dict = {r.header_id: float(r.total_received or 0) for r in receipts_data}

    # REF数量
    ref_counts = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectRef.id).label('ref_count')
    ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()
    ref_count_dict = {r.header_id: r.ref_count for r in ref_counts}

    # 有发票的REF数量
    ref_with_invoice = db.session.query(
        ProjectRef.header_id,
        db.func.count(db.distinct(InvoiceItem.ref_id)).label('invoiced_ref_count')
    ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id).filter(
        ProjectRef.header_id.in_(project_ids)
    ).group_by(ProjectRef.header_id).all()
    invoiced_ref_dict = {r.header_id: r.invoiced_ref_count for r in ref_with_invoice}

    # EO数量
    eo_counts = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectEO.id).label('eo_count')
    ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
        ProjectRef.header_id.in_(project_ids)
    ).group_by(ProjectRef.header_id).all()
    eo_count_dict = {r.header_id: r.eo_count for r in eo_counts}

    # 已付款EO数量（is_paid == True 视为已付款）
    eo_paid_counts = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectEO.id).label('paid_eo_count')
    ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
        ProjectRef.header_id.in_(project_ids),
        ProjectEO.is_paid == True
    ).group_by(ProjectRef.header_id).all()
    paid_eo_dict = {r.header_id: r.paid_eo_count for r in eo_paid_counts}

    # 构建统计字典
    for project_id in project_ids:
        ref_info = next((r for r in refs_data if r.header_id == project_id), None)
        total_selling = float(ref_info.total_selling or 0) if ref_info else 0
        total_cost = float(ref_info.total_cost or 0) if ref_info else 0
        total_received = receipts_dict.get(project_id, 0)
        balance = total_selling - total_received

        ref_count = ref_count_dict.get(project_id, 0)
        invoiced_ref_count = invoiced_ref_dict.get(project_id, 0)
        eo_count = eo_count_dict.get(project_id, 0)
        paid_eo_count = paid_eo_dict.get(project_id, 0)

        # 计算是否可结算
        all_refs_invoiced = ref_count > 0 and ref_count == invoiced_ref_count
        all_eos_paid = eo_count == 0 or (eo_count > 0 and eo_count == paid_eo_count)
        balance_cleared = abs(balance) < 0.01

        can_settle = all_refs_invoiced and all_eos_paid and balance_cleared

        project_stats[project_id] = {
            'total_selling_price': total_selling,
            'total_cost_price': total_cost,
            'total_profit': total_selling - total_cost,
            'total_received': total_received,
            'balance': balance,
            'ref_count': ref_count,
            'invoiced_ref_count': invoiced_ref_count,
            'eo_count': eo_count,
            'paid_eo_count': paid_eo_count,
            'can_settle': can_settle
        }

    return project_stats


def _calculate_stats(project_stats, base_query=None):
    """计算统计数据（基于筛选后的全部数据）"""
    # 基于筛选后的数据计算结算状态统计
    if base_query is not None:
        # 从筛选后的查询中统计
        settled_count = base_query.filter(ProjectHeader.is_settled == True).count()
        unsettled_count = base_query.filter(ProjectHeader.is_settled == False).count()
    else:
        # 全局统计（兜底）
        settled_count = ProjectHeader.query.filter(ProjectHeader.is_settled == True).count()
        unsettled_count = ProjectHeader.query.filter(ProjectHeader.is_settled == False).count()

    # 筛选后全部数据的汇总统计
    page_total_selling = sum(s.get('total_selling_price', 0) for s in project_stats.values())
    page_total_cost = sum(s.get('total_cost_price', 0) for s in project_stats.values())
    page_total_profit = sum(s.get('total_profit', 0) for s in project_stats.values())
    page_total_received = sum(s.get('total_received', 0) for s in project_stats.values())
    page_total_balance = sum(s.get('balance', 0) for s in project_stats.values())

    # 计算可结算数量（筛选后全部数据中）
    can_settle_count = sum(1 for s in project_stats.values() if s.get('can_settle'))

    # 利润分配汇总（需要从数据库查询筛选后的项目）
    page_operator_profit = 0
    page_sales_profit = 0
    page_company_profit = 0

    if project_stats:
        project_ids = list(project_stats.keys())
        profit_data = db.session.query(
            db.func.sum(ProjectHeader.operator_profit),
            db.func.sum(ProjectHeader.sales_profit),
            db.func.sum(ProjectHeader.company_profit)
        ).filter(ProjectHeader.id.in_(project_ids)).first()

        if profit_data:
            page_operator_profit = float(profit_data[0] or 0)
            page_sales_profit = float(profit_data[1] or 0)
            page_company_profit = float(profit_data[2] or 0)

    return {
        'can_settle_count': can_settle_count,
        'settled_count': settled_count,
        'unsettled_count': unsettled_count,
        'page_total_selling': page_total_selling,
        'page_total_cost': page_total_cost,
        'page_total_profit': page_total_profit,
        'page_total_received': page_total_received,
        'page_total_balance': page_total_balance,
        'page_operator_profit': page_operator_profit,
        'page_sales_profit': page_sales_profit,
        'page_company_profit': page_company_profit,
        'total_count': len(project_stats)  # 筛选后的总数
    }


@bp.route('/api/preview_voucher_no', methods=['GET'])
@login_required
@staff_only
def preview_voucher_no():
    """预览下一个结算凭证号"""
    try:
        from App_new.business.projects.models.payment_voucher import PaymentVoucher
        voucher_no = PaymentVoucher.generate_voucher_no()
        return jsonify({'success': True, 'voucher_no': voucher_no})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@bp.route('/api/batch_settle', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def batch_settle():
    """批量结算项目，生成结算凭证"""
    try:
        from App_new.business.projects.models.payment_voucher import PaymentVoucher
        from decimal import Decimal

        data = request.get_json()
        project_ids = data.get('project_ids', [])
        remarks = data.get('remarks', '')
        settle_date_str = data.get('settle_date', '')

        if not project_ids:
            return jsonify({'success': False, 'message': '请选择要结算的项目'})

        # 解析结算日期
        if settle_date_str:
            try:
                settle_date = datetime.strptime(settle_date_str, '%Y-%m-%d')
            except ValueError:
                settle_date = datetime.now()
        else:
            settle_date = datetime.now()

        # 查询所有要结算的项目
        projects_to_settle = []
        for project_id in project_ids:
            project = ProjectHeader.query.get(project_id)
            if project and not project.is_settled:
                projects_to_settle.append(project)

        if not projects_to_settle:
            return jsonify({'success': False, 'message': '没有可结算的项目'})

        # 计算汇总信息
        total_selling = Decimal('0')
        total_cost = Decimal('0')
        total_profit = Decimal('0')
        total_operator_profit = Decimal('0')
        total_sales_profit = Decimal('0')
        total_company_profit = Decimal('0')

        for project in projects_to_settle:
            # 查询项目的 REF 汇总
            refs = ProjectRef.query.filter_by(header_id=project.id).all()
            project_selling = sum(Decimal(str(r.selling_price or 0)) for r in refs)
            project_cost = sum(Decimal(str(r.cost_price or 0)) for r in refs)

            total_selling += project_selling
            total_cost += project_cost
            total_profit += (project_selling - project_cost)
            total_operator_profit += Decimal(str(project.operator_profit or 0))
            total_sales_profit += Decimal(str(project.sales_profit or 0))
            total_company_profit += Decimal(str(project.company_profit or 0))

        # 创建结算凭证
        voucher = PaymentVoucher(
            voucher_no=PaymentVoucher.generate_voucher_no(),
            settle_date=settle_date,
            settled_by=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
            project_count=len(projects_to_settle),
            total_selling=total_selling,
            total_cost=total_cost,
            total_profit=total_profit,
            total_operator_profit=total_operator_profit,
            total_sales_profit=total_sales_profit,
            total_company_profit=total_company_profit,
            remarks=remarks
        )
        db.session.add(voucher)
        db.session.flush()  # 获取 voucher.id

        # 更新项目结算状态并关联凭证
        success_count = 0
        for project in projects_to_settle:
            project.is_settled = True
            project.settled_at = settle_date
            project.settled_by = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
            project.payment_voucher_id = voucher.id
            success_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功结算 {success_count} 个项目，凭证号：{voucher.voucher_no}',
            'voucher_no': voucher.voucher_no,
            'voucher_id': voucher.id
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'批量结算失败: {str(e)}'})


@bp.route('/api/batch_unsettle', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def batch_unsettle():
    """批量取消结算"""
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])

        if not project_ids:
            return jsonify({'success': False, 'message': '请选择要取消结算的项目'})

        success_count = 0

        for project_id in project_ids:
            project = ProjectHeader.query.get(project_id)
            if project and project.is_settled:
                project.is_settled = False
                project.settled_at = None
                project.settled_by = None
                project.payment_voucher_id = None  # 清除凭证关联
                success_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功取消结算 {success_count} 个项目'
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'批量取消结算失败: {str(e)}'})


@bp.route('/export')
@login_required
@staff_only
def export_excel():
    """导出结算列表为Excel"""
    try:
        # 获取筛选参数
        search = request.args.get('search', '')
        staff_id = request.args.get('staff_id', '', type=int) if request.args.get('staff_id') else ''
        settlement_status = request.args.get('settlement_status', '')
        profit_status = request.args.get('profit_status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        # 构建查询
        base_query = ProjectHeader.query.options(
            db.joinedload(ProjectHeader.company)
        )

        if search:
            base_query = base_query.outerjoin(CustomerCompany).filter(
                db.or_(
                    ProjectHeader.hid.like(f'%{search}%'),
                    CustomerCompany.company_name.like(f'%{search}%')
                )
            )

        if staff_id:
            base_query = base_query.filter(ProjectHeader.staff_id == staff_id)

        if date_from:
            base_query = base_query.filter(ProjectHeader.created_at >= date_from)
        if date_to:
            base_query = base_query.filter(ProjectHeader.created_at <= date_to + ' 23:59:59')

        if settlement_status:
            if settlement_status == 'settled':
                base_query = base_query.filter(ProjectHeader.is_settled == True)
            elif settlement_status == 'unsettled':
                base_query = base_query.filter(ProjectHeader.is_settled == False)
            elif settlement_status == 'can_settle':
                base_query = base_query.filter(ProjectHeader.is_settled == False)
                base_query = _apply_can_settle_filter(base_query)

        if profit_status:
            profit_subquery = db.session.query(ProjectRef.header_id).group_by(ProjectRef.header_id)
            if profit_status == 'profit':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) > 0
                )
            elif profit_status == 'loss':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) < 0
                )
            elif profit_status == 'zero':
                profit_subquery = profit_subquery.having(
                    db.func.sum(ProjectRef.selling_price) - db.func.sum(ProjectRef.cost_price) == 0
                )
            base_query = base_query.filter(ProjectHeader.id.in_(profit_subquery))

        base_query = base_query.order_by(ProjectHeader.created_at.desc())
        projects = base_query.all()

        # 获取统计信息
        project_ids = [p.id for p in projects]
        project_stats = _get_project_stats(project_ids)

        # 构建Excel数据
        data = []
        for project in projects:
            pstats = project_stats.get(project.id, {})
            data.append({
                'HID': project.hid or '',
                '公司名称': project.company.company_name if project.company else '',
                '创建日期': project.created_at.strftime('%Y-%m-%d') if project.created_at else '',
                '经办人': project.staff_display_name,
                '销售金额': pstats.get('total_selling_price', 0),
                '成本': pstats.get('total_cost_price', 0),
                '利润': pstats.get('total_profit', 0),
                '收款': pstats.get('total_received', 0),
                '余额': pstats.get('balance', 0),
                'REF数': pstats.get('ref_count', 0),
                '已开票REF': pstats.get('invoiced_ref_count', 0),
                'EO数': pstats.get('eo_count', 0),
                '已付款EO': pstats.get('paid_eo_count', 0),
                '订单类型': project.order_type or '',
                '操作员利润': float(project.operator_profit) if project.operator_profit else 0.00,
                '业务员利润': float(project.sales_profit) if project.sales_profit else 0.00,
                '公司利润': float(project.company_profit) if project.company_profit else 0.00,
                '结算状态': '已结算' if project.is_settled else ('可结算' if pstats.get('can_settle') else '未结算'),
                '凭证号': project.payment_voucher.voucher_no if project.payment_voucher else '',
                '结算时间': project.settled_at.strftime('%Y-%m-%d %H:%M') if project.settled_at else '',
                '结算人': project.settled_by or ''
            })

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='项目结算')

        output.seek(0)
        filename = f'项目结算_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


@bp.route('/api/calculate_profit_distribution', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def calculate_profit_distribution():
    """计算并更新利润分配（选中项目）"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution as calc_profit, get_order_type
        from decimal import Decimal

        data = request.get_json()
        project_ids = data.get('project_ids', [])

        if not project_ids:
            return jsonify({'success': False, 'message': '请选择要计算的项目'})

        success_count = 0
        error_count = 0
        errors = []

        for project_id in project_ids:
            try:
                project = ProjectHeader.query.get(project_id)
                if not project:
                    error_count += 1
                    errors.append(f'项目 ID {project_id} 不存在')
                    continue

                # 计算项目利润
                refs = ProjectRef.query.filter_by(header_id=project_id).all()
                total_selling = sum(float(r.selling_price or 0) for r in refs)
                total_cost = sum(float(r.cost_price or 0) for r in refs)
                profit = Decimal(str(total_selling - total_cost))

                # 获取订单类型
                order_type = get_order_type(profit)

                # 计算利润分配
                if profit == 0:
                    project.operator_profit = Decimal('0')
                    project.sales_profit = Decimal('0')
                    project.company_profit = Decimal('0')
                    project.order_type = order_type
                else:
                    operator_profit, sales_profit, company_profit = calc_profit(profit)
                    project.operator_profit = operator_profit
                    project.sales_profit = sales_profit
                    project.company_profit = company_profit
                    project.order_type = order_type

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f'项目 {project_id} 计算失败: {str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功计算 {success_count} 个项目的利润分配' + (f'，{error_count} 个失败' if error_count > 0 else ''),
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10] if errors else []
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'计算失败: {str(e)}'})


@bp.route('/api/calculate_all_unsettled_profit_distribution', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def calculate_all_unsettled_profit_distribution():
    """计算全部未结算项目的利润分配"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution as calc_profit, get_order_type
        from decimal import Decimal

        # 查询所有未结算项目
        unsettled_projects = ProjectHeader.query.filter(ProjectHeader.is_settled == False).all()

        if not unsettled_projects:
            return jsonify({'success': False, 'message': '没有未结算的项目'})

        success_count = 0
        error_count = 0
        errors = []

        for project in unsettled_projects:
            try:
                # 计算项目利润
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                total_selling = sum(float(r.selling_price or 0) for r in refs)
                total_cost = sum(float(r.cost_price or 0) for r in refs)
                profit = Decimal(str(total_selling - total_cost))

                # 获取订单类型
                order_type = get_order_type(profit)

                # 计算利润分配
                if profit == 0:
                    project.operator_profit = Decimal('0')
                    project.sales_profit = Decimal('0')
                    project.company_profit = Decimal('0')
                    project.order_type = order_type
                else:
                    operator_profit, sales_profit, company_profit = calc_profit(profit)
                    project.operator_profit = operator_profit
                    project.sales_profit = sales_profit
                    project.company_profit = company_profit
                    project.order_type = order_type

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f'项目 {project.hid} 计算失败: {str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功计算 {success_count} 个未结算项目的利润分配' + (f'，{error_count} 个失败' if error_count > 0 else ''),
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10] if errors else []
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'计算失败: {str(e)}'})


@bp.route('/vouchers')
@login_required
@staff_only
def voucher_list():
    """结算凭证列表页面"""
    try:
        from App_new.business.projects.models.payment_voucher import PaymentVoucher

        # 获取筛选参数
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20

        # 构建查询
        query = PaymentVoucher.query

        # 搜索凭证号
        if search:
            query = query.filter(PaymentVoucher.voucher_no.like(f'%{search}%'))

        # 日期筛选（转换为 datetime 对象）
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(PaymentVoucher.settle_date >= date_from_dt)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
                query = query.filter(PaymentVoucher.settle_date <= date_to_dt)
            except ValueError:
                pass

        # 排序
        query = query.order_by(PaymentVoucher.settle_date.desc())

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        vouchers = pagination.items

        # 计算汇总
        total_stats = {
            'total_vouchers': PaymentVoucher.query.count(),
            'total_projects': db.session.query(db.func.sum(PaymentVoucher.project_count)).scalar() or 0,
            'total_profit': float(db.session.query(db.func.sum(PaymentVoucher.total_profit)).scalar() or 0)
        }

        # 构建查询字符串
        query_params = []
        if search:
            query_params.append(f'search={search}')
        if date_from:
            query_params.append(f'date_from={date_from}')
        if date_to:
            query_params.append(f'date_to={date_to}')
        query_string = '&'.join(query_params)

        return render_template(
            'business/projects/voucher_list.html',
            vouchers=vouchers,
            pagination=pagination,
            total_stats=total_stats,
            query_string=query_string,
            filters={
                'search': search,
                'date_from': date_from,
                'date_to': date_to
            }
        )

    except Exception as e:
        traceback.print_exc()
        return render_template(
            'business/projects/voucher_list.html',
            vouchers=[],
            pagination=None,
            total_stats={'total_vouchers': 0, 'total_projects': 0, 'total_profit': 0},
            query_string='',
            filters={}
        )


@bp.route('/vouchers/<int:voucher_id>')
@login_required
@staff_only
def voucher_detail(voucher_id):
    """结算凭证详情页面"""
    try:
        from App_new.business.projects.models.payment_voucher import PaymentVoucher

        voucher = PaymentVoucher.query.get_or_404(voucher_id)

        # 获取关联的项目
        projects = ProjectHeader.query.filter_by(payment_voucher_id=voucher_id).all()

        # 获取项目统计信息
        project_ids = [p.id for p in projects]
        project_stats = _get_project_stats(project_ids) if project_ids else {}

        return render_template(
            'business/projects/voucher_detail.html',
            voucher=voucher,
            projects=projects,
            project_stats=project_stats
        )

    except Exception as e:
        traceback.print_exc()
        from flask import flash, redirect, url_for
        flash(f'加载凭证详情失败: {str(e)}', 'error')
        return redirect(url_for('business_projects.settlement.voucher_list'))
