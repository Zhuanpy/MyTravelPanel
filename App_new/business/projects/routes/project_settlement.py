# -*- coding: utf-8 -*-
"""
项目结算路由

只做查看：列表、筛选、导出。结算与利润分配统一在业绩结算页
（statement_routes.performance_settlement）操作，这里不再提供入口。
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from App_new.exts import db
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

        # 构建操作员/业务员名字映射
        # 以全量用户为底：staff_list 过滤了 is_active，离职员工的历史项目
        # 只用它会查不到名字、显示成 ID:23
        from App_new.utils.staff_names import get_user_name_map
        staff_name_map = get_user_name_map()
        staff_name_map.update({s['id']: s['name'] for s in staff_list})
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

    # 批量查询收款数据：走「发票分配表 + REF级直接收款」，不能把本项目名下的收款直接相加。
    # 一笔项目级收款可能跨项目分配（如 H808 名下 695，其中 345 属于 H810），
    # 直接相加会让付款方显示超收、被分配方显示未收款，两边都结算不了。
    from App_new.business.projects.models.receipt import ReceiptInvoiceAllocation
    from App_new.business.projects.models.invoice import ProjectInvoice

    receipts_dict = {}
    for row in db.session.query(
        ProjectInvoice.header_id,
        db.func.sum(ReceiptInvoiceAllocation.allocated_amount).label('total')
    ).join(
        ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
    ).join(
        ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
    ).filter(
        ProjectInvoice.header_id.in_(project_ids),
        ProjectReceipt.status == 'confirmed',
        ProjectReceipt.ref_id.is_(None)
    ).group_by(ProjectInvoice.header_id).all():
        receipts_dict[row.header_id] = float(row.total or 0)

    for row in db.session.query(
        ProjectReceipt.header_id,
        db.func.sum(ProjectReceipt.amount).label('total')
    ).filter(
        ProjectReceipt.header_id.in_(project_ids),
        ProjectReceipt.status == 'confirmed',
        ProjectReceipt.ref_id.isnot(None)
    ).group_by(ProjectReceipt.header_id).all():
        receipts_dict[row.header_id] = receipts_dict.get(row.header_id, 0) + float(row.total or 0)

    # REF数量
    ref_counts = db.session.query(
        ProjectRef.header_id,
        db.func.count(ProjectRef.id).label('ref_count')
    ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()
    ref_count_dict = {r.header_id: r.ref_count for r in ref_counts}

    # 是否所有 REF 都已开票：走 ProjectInvoice.ref_ids，与 settle_blockers / is_invoiced 同源。
    # 不能数 invoice_items——只有 334/546 张发票有明细行，会把业务上已完成的项目误判成未开票
    fully_invoiced_dict = ProjectRef.get_headers_fully_invoiced(project_ids)

    # 未收款：按未作废发票的未收合计（收款只能分配到发票，能收的上限就是它）
    unpaid_dict = {}
    for row in db.session.query(
        ProjectInvoice.header_id,
        db.func.sum(db.func.greatest(ProjectInvoice.amount - ProjectInvoice.paid_amount, 0)).label('unpaid')
    ).filter(
        ProjectInvoice.header_id.in_(project_ids),
        ProjectInvoice.status != 'cancelled'
    ).group_by(ProjectInvoice.header_id).all():
        unpaid_dict[row.header_id] = float(row.unpaid or 0)

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
        invoiced_ref_count = ref_count if fully_invoiced_dict.get(project_id) else 0
        eo_count = eo_count_dict.get(project_id, 0)
        paid_eo_count = paid_eo_dict.get(project_id, 0)

        # 可结算条件：与 ProjectHeader.settle_blockers 完全一致
        # （每条 REF 都要有 EO；EO 以 is_paid 为准，不看 pay_amount）
        all_refs_have_eo = ref_count > 0 and ref_count == eo_count
        all_eos_paid = eo_count > 0 and eo_count == paid_eo_count
        all_refs_invoiced = fully_invoiced_dict.get(project_id, False)
        # 未收款以发票未收合计为准（与 settle_blockers 同源）；
        # 「REF售价合计 − 已收」是另一套账，REF售价与实际开票金额可能不一致
        balance_cleared = unpaid_dict.get(project_id, 0.0) < 0.01

        can_settle = all_refs_have_eo and all_eos_paid and all_refs_invoiced and balance_cleared

        project_stats[project_id] = {
            'total_selling_price': total_selling,
            'total_cost_price': total_cost,
            'total_profit': total_selling - total_cost,
            'total_received': total_received,
            'balance': balance,
            'ref_count': ref_count,
            'invoiced_ref_count': ref_count if fully_invoiced_dict.get(project_id) else 0,
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


# 批量结算 / 取消结算已移除：结算统一走业绩结算页 statement_routes.performance_settlement。
# 这里曾经是第二套结算入口，产出的记录和口径都与那边不一致。


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


# 利润分配接口已移除：分配在业绩结算页操作，结算时也会按当前 REF 自动重算。


