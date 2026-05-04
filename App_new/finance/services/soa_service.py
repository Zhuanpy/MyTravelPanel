# -*- coding: utf-8 -*-
"""
SOA (Statement of Account) 生成服务
用于生成客户对账单 - 基于 Project 数据
"""

import json
from datetime import datetime
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.business.flight.models.flight import ProjectFlightSegment
from flask import render_template
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from sqlalchemy import union_all


class SOAService:
    """SOA生成服务 - 基于 Project 数据"""

    def __init__(self):
        pass

    def _resolve_date_range(self, month=None, start_date=None, end_date=None):
        """根据 month / start_date / end_date 解析出 BK.DATE 的过滤区间 [start, end)。

        优先级：start_date / end_date 任一存在时按区间过滤（忽略 month）；
        否则回退到 month（按整月过滤）。返回 (start, end_exclusive)；
        任一边界为 None 表示该侧不限。解析失败的字段视为未提供。
        """
        from datetime import date, timedelta

        def _parse(s):
            if not s:
                return None
            try:
                return datetime.strptime(s, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None

        start = _parse(start_date)
        end_inclusive = _parse(end_date)

        if start is not None or end_inclusive is not None:
            # 用户显式指定区间：end_date 是包含日，转为半开区间右端 +1 天
            end_exclusive = (end_inclusive + timedelta(days=1)) if end_inclusive else None
            return start, end_exclusive

        if month:
            try:
                year, month_num = month.split('-')
                year = int(year)
                month_num = int(month_num)
                month_start = date(year, month_num, 1)
                month_end = date(year + 1, 1, 1) if month_num == 12 else date(year, month_num + 1, 1)
                return month_start, month_end
            except (ValueError, TypeError):
                pass

        return None, None

    def _calculate_project_balance(self, project_id, total_selling):
        """计算项目余额（销售金额 - 已收款金额）"""
        try:
            # 方式1: 通过发票分配表统计（项目级别收款）
            alloc_total = db.session.query(
                db.func.coalesce(db.func.sum(ReceiptInvoiceAllocation.allocated_amount), 0)
            ).join(
                ProjectInvoice, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
            ).join(
                ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
            ).filter(
                ProjectInvoice.header_id == project_id,
                ProjectReceipt.status == 'confirmed',
                ProjectReceipt.ref_id == None
            ).scalar() or 0

            # 方式2: REF级别直接收款
            ref_receipt_total = db.session.query(
                db.func.coalesce(db.func.sum(ProjectReceipt.amount), 0)
            ).filter(
                ProjectReceipt.header_id == project_id,
                ProjectReceipt.status == 'confirmed',
                ProjectReceipt.ref_id.isnot(None)
            ).scalar() or 0

            # 方式3: 旧项目级别收款（没有分配记录也没有ref_id）
            old_receipts_subq = db.session.query(
                ReceiptInvoiceAllocation.receipt_id
            ).distinct().subquery()

            old_receipt_total = db.session.query(
                db.func.coalesce(db.func.sum(ProjectReceipt.amount), 0)
            ).filter(
                ProjectReceipt.header_id == project_id,
                ProjectReceipt.status == 'confirmed',
                ProjectReceipt.ref_id == None,
                ~ProjectReceipt.id.in_(old_receipts_subq)
            ).scalar() or 0

            total_received = float(alloc_total) + float(ref_receipt_total) + float(old_receipt_total)
            balance = float(total_selling) - total_received
            return balance
        except Exception as e:
            print(f"计算项目 {project_id} 余额时出错: {e}")
            return float(total_selling)

    def _get_project_departure_date(self, ref_id):
        """从REF的航段中获取出发日期"""
        try:
            # 获取第一个航段的出发时间
            first_segment = ProjectFlightSegment.query.filter_by(
                ref_id=ref_id
            ).order_by(ProjectFlightSegment.departure_time).first()

            if first_segment and first_segment.departure_time:
                return first_segment.departure_time.strftime('%Y-%m-%d')
        except Exception:
            pass
        return ''

    def get_soa_list(self, page=1, per_page=20, search=None, month=None, company=None, group=None, balance_positive=False, profit_loss=None, start_date=None, end_date=None):
        """获取可生成SOA的项目列表"""
        try:
            query = ProjectHeader.query.options(
                db.joinedload(ProjectHeader.company)
            )

            if search:
                search_lower = search.lower()
                query = query.filter(
                    db.or_(
                        ProjectHeader.hid.ilike(f'%{search_lower}%'),
                        ProjectHeader.desc.ilike(f'%{search_lower}%'),
                        ProjectHeader.contact.ilike(f'%{search_lower}%'),
                        ProjectHeader.leader_name.ilike(f'%{search_lower}%')
                    )
                )

            # 公司过滤
            if company:
                query = query.join(CustomerCompany).filter(CustomerCompany.company_name == company)
            elif group:
                # 集团过滤（只在没有指定公司时生效）
                query = query.join(CustomerCompany).filter(CustomerCompany.group_name == group)

            # BK.DATE 过滤：start_date/end_date 优先，否则回退到 month
            range_start, range_end = self._resolve_date_range(month=month, start_date=start_date, end_date=end_date)
            if range_start is not None:
                query = query.filter(ProjectHeader.created_at >= range_start)
            if range_end is not None:
                query = query.filter(ProjectHeader.created_at < range_end)

            # 获取所有符合条件的项目（先不分页，因为需要计算余额后再过滤）
            # 如果按集团筛选，则先按公司名称排序，再按HID排序
            if group:
                all_headers = query.order_by(
                    CustomerCompany.company_name,
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()
            else:
                all_headers = query.order_by(
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()

            # 获取所有项目的财务数据
            all_project_ids = [h.id for h in all_headers]

            # 批量查询 REF 销售数据
            refs_data = {}
            if all_project_ids:
                refs_query = db.session.query(
                    ProjectRef.header_id,
                    db.func.sum(ProjectRef.selling_price).label('total_selling'),
                    db.func.sum(ProjectRef.cost_price).label('total_cost')
                ).filter(ProjectRef.header_id.in_(all_project_ids)).group_by(ProjectRef.header_id).all()

                for r in refs_query:
                    refs_data[r.header_id] = {
                        'total_selling': float(r.total_selling or 0),
                        'total_cost': float(r.total_cost or 0)
                    }

            # 构建所有项目数据并应用过滤
            all_headers_data = []
            for header in all_headers:
                ref_info = refs_data.get(header.id, {'total_selling': 0, 'total_cost': 0})
                total_selling = ref_info['total_selling']
                total_cost = ref_info['total_cost']
                profit = total_selling - total_cost
                balance = self._calculate_project_balance(header.id, total_selling)

                # 应用余额过滤
                if balance_positive and balance <= 0:
                    continue

                # 应用盈亏过滤
                if profit_loss:
                    if profit_loss == 'profit' and profit <= 0:
                        continue
                    elif profit_loss == 'loss' and profit >= 0:
                        continue
                    elif profit_loss == 'even' and profit != 0:
                        continue

                # 获取第一个REF的描述和出发日期
                first_ref = ProjectRef.query.filter_by(header_id=header.id).first()
                itin_desc = first_ref.description if first_ref and first_ref.description else header.desc

                # 从REF的航段获取出发日期
                dep_date = self._get_project_departure_date(first_ref.id) if first_ref else ''

                all_headers_data.append({
                    'id': header.id,
                    'booking_header_id': header.hid,
                    'corporate_name': header.company.company_name if header.company else None,
                    'book_date': header.created_at.strftime('%Y-%m-%d') if header.created_at else None,
                    'client_name': header.leader_member_name or header.leader_name or header.contact,
                    'dep_date': dep_date,
                    'itin_desc': itin_desc,
                    'invoice_no': None,
                    'invoice_date': None,
                    'sub_total_balance': balance,
                    'detail_count': ProjectRef.query.filter_by(header_id=header.id).count()
                })

            # 计算统计数据（基于所有过滤后的数据）
            total_balance = sum(h['sub_total_balance'] for h in all_headers_data)
            total_count = len(all_headers_data)

            # 在Python中进行分页
            total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            headers_data = all_headers_data[start_idx:end_idx]

            return {
                'headers': headers_data,
                'total': total_count,
                'pages': total_pages,
                'current_page': page,
                'per_page': per_page,
                'statistics': {
                    'total_balance': total_balance,
                    'total_count': total_count
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'获取SOA列表失败: {str(e)}'
            }

    def get_company_list(self, group=None):
        """获取所有公司列表，支持按集团筛选"""
        try:
            # 获取所有有项目的不重复公司名称
            query = db.session.query(CustomerCompany.company_name).join(
                ProjectHeader, ProjectHeader.company_id == CustomerCompany.id
            ).filter(
                CustomerCompany.company_name.isnot(None),
                CustomerCompany.company_name != ''
            )

            # 如果指定了集团，则只返回该集团下的公司
            if group:
                query = query.filter(CustomerCompany.group_name == group)

            companies = query.distinct().all()
            company_list = [company[0] for company in companies if company[0]]

            return {
                'success': True,
                'companies': company_list
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'获取公司列表失败: {str(e)}'
            }

    def get_group_list(self):
        """获取所有集团/关联标签列表"""
        try:
            # 获取所有有项目的不重复集团名称
            groups = db.session.query(CustomerCompany.group_name).join(
                ProjectHeader, ProjectHeader.company_id == CustomerCompany.id
            ).filter(
                CustomerCompany.group_name.isnot(None),
                CustomerCompany.group_name != ''
            ).distinct().all()

            group_list = [group[0] for group in groups if group[0]]

            return {
                'success': True,
                'groups': group_list
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'获取集团列表失败: {str(e)}'
            }

    def batch_download_soa(self, group=None, company=None, month=None, search=None, balance_positive=None, profit_loss=None, format='excel', start_date=None, end_date=None):
        """批量下载SOA - 生成Excel表格"""
        try:
            import pandas as pd

            # 构建查询条件
            query = ProjectHeader.query.options(
                db.joinedload(ProjectHeader.company)
            )

            if search:
                search_lower = search.lower()
                query = query.filter(
                    db.or_(
                        ProjectHeader.hid.ilike(f'%{search_lower}%'),
                        ProjectHeader.desc.ilike(f'%{search_lower}%'),
                        ProjectHeader.contact.ilike(f'%{search_lower}%'),
                        ProjectHeader.leader_name.ilike(f'%{search_lower}%')
                    )
                )

            if company:
                query = query.join(CustomerCompany).filter(CustomerCompany.company_name == company)
            elif group:
                # 集团过滤（只在没有指定公司时生效）
                query = query.join(CustomerCompany).filter(CustomerCompany.group_name == group)

            # BK.DATE 过滤：start_date/end_date 优先，否则回退到 month
            range_start, range_end = self._resolve_date_range(month=month, start_date=start_date, end_date=end_date)
            if range_start is not None:
                query = query.filter(ProjectHeader.created_at >= range_start)
            if range_end is not None:
                query = query.filter(ProjectHeader.created_at < range_end)

            # 获取所有符合条件的项目
            # 如果按集团筛选，则先按公司名称排序，再按HID排序
            if group:
                headers = query.order_by(
                    CustomerCompany.company_name,
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()
            else:
                headers = query.order_by(
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()

            if not headers:
                return None, "没有找到符合条件的SOA数据"

            # 批量获取财务数据
            project_ids = [h.id for h in headers]
            refs_data = {}
            if project_ids:
                refs_query = db.session.query(
                    ProjectRef.header_id,
                    db.func.sum(ProjectRef.selling_price).label('total_selling'),
                    db.func.sum(ProjectRef.cost_price).label('total_cost')
                ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()

                for r in refs_query:
                    refs_data[r.header_id] = {
                        'total_selling': float(r.total_selling or 0),
                        'total_cost': float(r.total_cost or 0)
                    }

            # 准备Excel数据
            excel_data = []

            for header in headers:
                ref_info = refs_data.get(header.id, {'total_selling': 0, 'total_cost': 0})
                total_selling = ref_info['total_selling']
                total_cost = ref_info['total_cost']
                profit = total_selling - total_cost
                balance = self._calculate_project_balance(header.id, total_selling)

                # 应用余额过滤
                if balance_positive and balance <= 0:
                    continue

                # 应用盈亏过滤
                if profit_loss:
                    if profit_loss == 'profit' and profit <= 0:
                        continue
                    elif profit_loss == 'loss' and profit >= 0:
                        continue
                    elif profit_loss == 'even' and profit != 0:
                        continue

                # 获取第一个REF的描述和出发日期
                first_ref = ProjectRef.query.filter_by(header_id=header.id).first()
                itin_desc = first_ref.description if first_ref and first_ref.description else header.desc

                # 从REF的航段获取出发日期
                dep_date = self._get_project_departure_date(first_ref.id) if first_ref else ''

                # 构建Excel行数据
                row_data = {
                    'HID': header.hid,
                    'COMPANY': header.company.company_name if header.company else '',
                    'BK.DATE': header.created_at.strftime('%Y-%m-%d') if header.created_at else '',
                    'CLIENT NAME': header.leader_member_name or header.leader_name or header.contact or '',
                    'DP.DATE': dep_date,
                    'ITIN DESCRIPTION': itin_desc or '',
                    'CCY': 'SGD',
                    'BAL': balance
                }

                excel_data.append(row_data)

            if not excel_data:
                return None, "没有找到符合条件的SOA数据"

            # 按公司分组，每家公司加一行小计；最后视情况加总计
            # 用稳定排序仅按公司名分组，保留每家公司内部已有的 HID 排序
            excel_data.sort(key=lambda row: (row['COMPANY'] or ''))

            final_rows = []
            subtotal_row_indices = []  # 标记小计行（用于样式），0-based 在 final_rows 中
            companies_seen = []
            current_company = None
            company_subtotal = 0.0
            company_count = 0
            grand_total = 0.0

            def _append_subtotal(company, subtotal, count):
                final_rows.append({
                    'HID': '',
                    'COMPANY': company or '',
                    'BK.DATE': '',
                    'CLIENT NAME': '',
                    'DP.DATE': '',
                    'ITIN DESCRIPTION': f'SUBTOTAL ({count} item{"s" if count > 1 else ""})',
                    'CCY': 'SGD',
                    'BAL': subtotal
                })
                subtotal_row_indices.append(len(final_rows) - 1)

            for row in excel_data:
                if current_company is None:
                    current_company = row['COMPANY']
                elif row['COMPANY'] != current_company:
                    _append_subtotal(current_company, company_subtotal, company_count)
                    companies_seen.append(current_company)
                    current_company = row['COMPANY']
                    company_subtotal = 0.0
                    company_count = 0

                final_rows.append(row)
                company_subtotal += row['BAL']
                company_count += 1
                grand_total += row['BAL']

            # 最后一家公司的小计
            _append_subtotal(current_company, company_subtotal, company_count)
            companies_seen.append(current_company)

            # 仅当有多家公司时才显示总计行（单家公司时小计即总计，避免重复）
            grand_total_row_index = None
            if len(companies_seen) > 1:
                final_rows.append({
                    'HID': '',
                    'COMPANY': '',
                    'BK.DATE': '',
                    'CLIENT NAME': '',
                    'DP.DATE': '',
                    'ITIN DESCRIPTION': 'GRAND TOTAL',
                    'CCY': 'SGD',
                    'BAL': grand_total
                })
                grand_total_row_index = len(final_rows) - 1

            df = pd.DataFrame(final_rows)

            # 生成Excel文件
            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='SOA Data', index=False)

                worksheet = writer.sheets['SOA Data']

                # 设置列宽
                column_widths = {
                    'A': 12,  # HID
                    'B': 25,  # COMPANY
                    'C': 12,  # BK.DATE
                    'D': 25,  # CLIENT NAME
                    'E': 12,  # DP.DATE
                    'F': 30,  # ITIN DESCRIPTION
                    'G': 8,   # CCY
                    'H': 12   # BAL
                }

                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width

                # 设置表头样式
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")

                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment

                # 设置数字格式
                for row in worksheet.iter_rows(min_row=2):
                    if len(row) > 7:
                        row[7].number_format = '$#,##0.00'

                # 小计行样式（浅黄底、加粗）；表头是第 1 行，数据从第 2 行开始
                subtotal_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
                subtotal_font = Font(bold=True, color="664D03")
                for idx in subtotal_row_indices:
                    excel_row_num = idx + 2
                    row_cells = worksheet[excel_row_num]
                    for cell in row_cells:
                        cell.fill = subtotal_fill
                        cell.font = subtotal_font
                    if len(row_cells) > 7:
                        row_cells[7].number_format = '$#,##0.00'

                # 总计行样式（仅当有多家公司时存在）
                if grand_total_row_index is not None:
                    excel_row_num = grand_total_row_index + 2
                    total_row = worksheet[excel_row_num]
                    total_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                    total_font = Font(bold=True, color="000080")
                    for cell in total_row:
                        cell.fill = total_fill
                        cell.font = total_font
                    if len(total_row) > 7:
                        total_row[7].number_format = '$#,##0.00'

                # 添加公司付款账户信息
                bank_info_start_row = worksheet.max_row + 3

                bank_info_font = Font(bold=False, color="000000")
                bank_title_font = Font(bold=True, color="000000")

                worksheet.cell(row=bank_info_start_row, column=1, value="JOYFUL ESCAPES PTE. LTD Bank Details:")
                worksheet.cell(row=bank_info_start_row, column=1).font = bank_title_font

                worksheet.cell(row=bank_info_start_row + 1, column=1, value="• OCBC Bank Singapore, AC No.: 5956-7793-1001")
                worksheet.cell(row=bank_info_start_row + 1, column=1).font = bank_info_font

                worksheet.cell(row=bank_info_start_row + 2, column=1, value="• PayNow UEN: 202337627W")
                worksheet.cell(row=bank_info_start_row + 2, column=1).font = bank_info_font

            excel_buffer.seek(0)
            return excel_buffer.getvalue(), None

        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, f"生成Excel文件时出错: {str(e)}"

    def batch_download_soa_pdf(self, group=None, company=None, month=None, search=None, balance_positive=None, profit_loss=None, start_date=None, end_date=None):
        """批量下载SOA - 生成PDF文件"""
        try:
            # 构建查询条件
            query = ProjectHeader.query.options(
                db.joinedload(ProjectHeader.company)
            )

            if search:
                search_lower = search.lower()
                query = query.filter(
                    db.or_(
                        ProjectHeader.hid.ilike(f'%{search_lower}%'),
                        ProjectHeader.desc.ilike(f'%{search_lower}%'),
                        ProjectHeader.contact.ilike(f'%{search_lower}%'),
                        ProjectHeader.leader_name.ilike(f'%{search_lower}%')
                    )
                )

            if company:
                query = query.join(CustomerCompany).filter(CustomerCompany.company_name == company)
            elif group:
                # 集团过滤（只在没有指定公司时生效）
                query = query.join(CustomerCompany).filter(CustomerCompany.group_name == group)

            # BK.DATE 过滤：start_date/end_date 优先，否则回退到 month
            range_start, range_end = self._resolve_date_range(month=month, start_date=start_date, end_date=end_date)
            if range_start is not None:
                query = query.filter(ProjectHeader.created_at >= range_start)
            if range_end is not None:
                query = query.filter(ProjectHeader.created_at < range_end)

            # 获取所有符合条件的项目
            # 如果按集团筛选，则先按公司名称排序，再按HID排序
            if group:
                headers = query.order_by(
                    CustomerCompany.company_name,
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()
            else:
                headers = query.order_by(
                    db.func.cast(db.func.substr(ProjectHeader.hid, 2), db.Integer).desc()
                ).all()

            if not headers:
                return None, "没有找到符合条件的SOA数据"

            # 批量获取财务数据
            project_ids = [h.id for h in headers]
            refs_data = {}
            if project_ids:
                refs_query = db.session.query(
                    ProjectRef.header_id,
                    db.func.sum(ProjectRef.selling_price).label('total_selling'),
                    db.func.sum(ProjectRef.cost_price).label('total_cost')
                ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()

                for r in refs_query:
                    refs_data[r.header_id] = {
                        'total_selling': float(r.total_selling or 0),
                        'total_cost': float(r.total_cost or 0)
                    }

            # 创建批量PDF换行样式
            batch_wrap_style = ParagraphStyle(
                'BatchWrapStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=8,
                leading=9,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )

            # 先收集每条数据，附带 company_name / balance 用于后续按公司分组求小计
            collected = []  # list of dict: {company, balance, row}
            for header in headers:
                ref_info = refs_data.get(header.id, {'total_selling': 0, 'total_cost': 0})
                total_selling = ref_info['total_selling']
                total_cost = ref_info['total_cost']
                profit = total_selling - total_cost
                balance = self._calculate_project_balance(header.id, total_selling)

                # 应用余额过滤
                if balance_positive and balance <= 0:
                    continue

                # 应用盈亏过滤
                if profit_loss:
                    if profit_loss == 'profit' and profit <= 0:
                        continue
                    elif profit_loss == 'loss' and profit >= 0:
                        continue
                    elif profit_loss == 'even' and profit != 0:
                        continue

                # 获取第一个REF的描述和出发日期
                first_ref = ProjectRef.query.filter_by(header_id=header.id).first()
                itin_desc = first_ref.description if first_ref and first_ref.description else header.desc
                dep_date = self._get_project_departure_date(first_ref.id) if first_ref else ''
                company_name = header.company.company_name if header.company else ''

                row_data = [
                    Paragraph(header.hid or '', batch_wrap_style),
                    Paragraph(company_name, batch_wrap_style),
                    Paragraph(header.created_at.strftime('%Y-%m-%d') if header.created_at else '', batch_wrap_style),
                    Paragraph(header.leader_member_name or header.leader_name or header.contact or '', batch_wrap_style),
                    Paragraph(dep_date, batch_wrap_style),  # DP.DATE
                    Paragraph(itin_desc or '', batch_wrap_style),
                    Paragraph('SGD', batch_wrap_style),
                    Paragraph(f"${balance:,.2f}", batch_wrap_style)
                ]

                collected.append({'company': company_name, 'balance': balance, 'row': row_data})

            if not collected:
                return None, "没有找到符合条件的SOA数据"

            # 按公司分组（稳定排序仅按公司名，公司内部保留 HID 排序）
            collected.sort(key=lambda r: r['company'] or '')

            # 小计/总计行样式
            subtotal_wrap_style = ParagraphStyle(
                'SubtotalWrapStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=8,
                leading=9,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )
            total_wrap_style = ParagraphStyle(
                'TotalWrapStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=8,
                leading=9,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )

            def _make_subtotal_row(company, subtotal, count):
                return [
                    Paragraph('', subtotal_wrap_style),
                    Paragraph(f"<b>{company or ''}</b>", subtotal_wrap_style),
                    Paragraph('', subtotal_wrap_style),
                    Paragraph('', subtotal_wrap_style),
                    Paragraph('', subtotal_wrap_style),
                    Paragraph(f"<b>SUBTOTAL ({count} item{'s' if count > 1 else ''})</b>", subtotal_wrap_style),
                    Paragraph('SGD', subtotal_wrap_style),
                    Paragraph(f"<b>${subtotal:,.2f}</b>", subtotal_wrap_style)
                ]

            # 拼装 pdf_data：每家公司块结束后插入小计行；并记录小计/总计行索引（在 pdf_data 中）
            pdf_data = []
            subtotal_pdf_indices = []
            companies_seen = []
            current_company = None
            company_subtotal = 0.0
            company_count = 0
            grand_total = 0.0

            for item in collected:
                if current_company is None:
                    current_company = item['company']
                elif item['company'] != current_company:
                    pdf_data.append(_make_subtotal_row(current_company, company_subtotal, company_count))
                    subtotal_pdf_indices.append(len(pdf_data) - 1)
                    companies_seen.append(current_company)
                    current_company = item['company']
                    company_subtotal = 0.0
                    company_count = 0

                pdf_data.append(item['row'])
                company_subtotal += item['balance']
                company_count += 1
                grand_total += item['balance']

            # 最后一家公司的小计
            pdf_data.append(_make_subtotal_row(current_company, company_subtotal, company_count))
            subtotal_pdf_indices.append(len(pdf_data) - 1)
            companies_seen.append(current_company)

            # 仅当有多家公司时才显示总计行
            grand_total_pdf_index = None
            if len(companies_seen) > 1:
                pdf_data.append([
                    Paragraph('', total_wrap_style),
                    Paragraph('', total_wrap_style),
                    Paragraph('', total_wrap_style),
                    Paragraph('', total_wrap_style),
                    Paragraph('', total_wrap_style),
                    Paragraph('<b>GRAND TOTAL</b>', total_wrap_style),
                    Paragraph('<b>SGD</b>', total_wrap_style),
                    Paragraph(f"<b>${grand_total:,.2f}</b>", total_wrap_style)
                ])
                grand_total_pdf_index = len(pdf_data) - 1

            # 生成PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER
            )

            story = []

            # 标题
            story.append(Paragraph("SOA Statement of Account", title_style))
            story.append(Spacer(1, 12))

            # 筛选条件说明（同时展示集团/公司/日期等条件）
            filter_parts = []
            if group:
                filter_parts.append(f"Group: {group}")
            if company:
                filter_parts.append(f"Company: {company}")
            # 日期区间优先于 month
            if start_date or end_date:
                filter_parts.append(f"BK.Date: {start_date or '...'} ~ {end_date or '...'}")
            elif month:
                filter_parts.append(f"Month: {month}")
            filter_text = " | ".join(filter_parts) if filter_parts else "All Data"

            story.append(Paragraph(filter_text, styles['Normal']))
            story.append(Spacer(1, 12))

            # 创建批量PDF表头换行样式
            batch_header_style = ParagraphStyle(
                'BatchHeaderStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=10,
                leading=12,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )

            # 创建表格
            table_data = [
                [Paragraph('HID', batch_header_style),
                 Paragraph('COMPANY', batch_header_style),
                 Paragraph('BK.DATE', batch_header_style),
                 Paragraph('CLIENT NAME', batch_header_style),
                 Paragraph('DP.DATE', batch_header_style),
                 Paragraph('ITIN DESCRIPTION', batch_header_style),
                 Paragraph('CCY', batch_header_style),
                 Paragraph('BAL', batch_header_style)]
            ] + pdf_data

            table = Table(table_data, colWidths=[0.6*inch, 1.85*inch, 0.8*inch, 1.5*inch, 0.8*inch, 1.85*inch, 0.6*inch, 0.8*inch])

            # 基础样式：表头绿、数据行浅灰、整表网格
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ]

            # 小计行：浅黄底、深棕字、加粗。pdf_data 索引 +1 即表格行索引（第 0 行是表头）
            for idx in subtotal_pdf_indices:
                row = idx + 1
                style_cmds.extend([
                    ('BACKGROUND', (0, row), (-1, row), colors.HexColor('#FFF3CD')),
                    ('TEXTCOLOR', (0, row), (-1, row), colors.HexColor('#664D03')),
                    ('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold'),
                ])

            # 总计行：浅绿底、深蓝字、加粗（仅当存在）
            if grand_total_pdf_index is not None:
                row = grand_total_pdf_index + 1
                style_cmds.extend([
                    ('BACKGROUND', (0, row), (-1, row), colors.HexColor('#e8f5e8')),
                    ('TEXTCOLOR', (0, row), (-1, row), colors.HexColor('#000080')),
                    ('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, row), (-1, row), 10),
                ])

            table.setStyle(TableStyle(style_cmds))
            story.append(table)

            # 银行信息
            batch_bank_style = ParagraphStyle(
                'BatchBankStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=9,
                leading=11,
                leftIndent=0,
                alignment=TA_LEFT
            )

            story.append(Spacer(1, 20))
            story.append(Paragraph("<b>JOYFUL ESCAPES PTE. LTD Bank Details:</b>", batch_bank_style))
            story.append(Paragraph("• OCBC Bank Singapore, AC No.: 5956-7793-1001", batch_bank_style))
            story.append(Paragraph("• PayNow UEN: 202337627W", batch_bank_style))
            story.append(Spacer(1, 20))

            doc.build(story)
            pdf_buffer.seek(0)

            return pdf_buffer.getvalue(), None

        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, f"生成PDF文件时出错: {str(e)}"

    # 以下方法保留用于单个项目预览（如果需要），但现在基于Project数据
    def generate_soa_html(self, header_id):
        """生成HTML格式的SOA（单个项目）"""
        try:
            header = ProjectHeader.query.options(
                db.joinedload(ProjectHeader.company)
            ).get(header_id)

            if not header:
                return None, "项目记录不存在"

            # 获取REF明细
            refs = ProjectRef.query.filter_by(header_id=header_id).all()

            # 计算财务数据
            total_selling = sum(float(r.selling_price or 0) for r in refs)
            total_cost = sum(float(r.cost_price or 0) for r in refs)
            balance = self._calculate_project_balance(header_id, total_selling)

            current_date = datetime.now().strftime('%Y-%m-%d')
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 获取联系人名称：优先从人员名单获取leader，其次使用header的leader_name或contact
            contact_name = header.leader_member_name or header.leader_name or header.contact or 'N/A'

            # 这里可以渲染一个新的模板，或者返回简单的HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>SOA - {header.hid}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #28a745; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #28a745; color: white; }}
                    .total {{ background-color: #e8f5e8; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>Statement of Account</h1>
                <p><strong>Project:</strong> {header.hid}</p>
                <p><strong>Company:</strong> {header.company.company_name if header.company else 'N/A'}</p>
                <p><strong>Contact:</strong> {contact_name}</p>
                <p><strong>Date:</strong> {current_date}</p>

                <table>
                    <thead>
                        <tr>
                            <th>REF</th>
                            <th>Description</th>
                            <th>Selling</th>
                            <th>Cost</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for ref in refs:
                html_content += f"""
                        <tr>
                            <td>{ref.ref_number}</td>
                            <td>{ref.description or ref.detailed_description or ''}</td>
                            <td>${float(ref.selling_price or 0):,.2f}</td>
                            <td>${float(ref.cost_price or 0):,.2f}</td>
                        </tr>
                """

            html_content += f"""
                        <tr class="total">
                            <td colspan="2">Total</td>
                            <td>${total_selling:,.2f}</td>
                            <td>${total_cost:,.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <p style="margin-top: 20px;"><strong>Balance Due:</strong> ${balance:,.2f}</p>

                <hr style="margin-top: 30px;">
                <p><strong>JOYFUL ESCAPES PTE. LTD Bank Details:</strong></p>
                <p>• OCBC Bank Singapore, AC No.: 5956-7793-1001</p>
                <p>• PayNow UEN: 202337627W</p>

                <p style="margin-top: 20px; color: #666; font-size: 12px;">Generated: {current_datetime}</p>
            </body>
            </html>
            """

            return html_content, None

        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, f"生成SOA时出错: {str(e)}"

    def generate_soa_pdf(self, header_id):
        """生成PDF格式的SOA（单个项目）"""
        try:
            header = ProjectHeader.query.options(
                db.joinedload(ProjectHeader.company)
            ).get(header_id)

            if not header:
                return None, "项目记录不存在"

            refs = ProjectRef.query.filter_by(header_id=header_id).all()

            total_selling = sum(float(r.selling_price or 0) for r in refs)
            total_cost = sum(float(r.cost_price or 0) for r in refs)
            balance = self._calculate_project_balance(header_id, total_selling)

            # 创建PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER
            )

            story = []

            story.append(Paragraph("Statement of Account", title_style))
            story.append(Spacer(1, 20))

            # 获取联系人名称：优先从人员名单获取leader
            contact_name = header.leader_member_name or header.leader_name or header.contact or 'N/A'

            # 项目信息
            company_info = [
                ['Project Information', 'Statement Information'],
                [f'Project: {header.hid}', f'Date: {datetime.now().strftime("%Y-%m-%d")}'],
                [f'Company: {header.company.company_name if header.company else "N/A"}', f'Currency: SGD'],
                [f'Contact: {contact_name}', '']
            ]

            company_table = Table(company_info, colWidths=[4.5*inch, 4.5*inch])
            company_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))

            story.append(company_table)
            story.append(Spacer(1, 20))

            # REF明细
            story.append(Paragraph("Transaction Details", styles['Heading2']))

            wrap_style = ParagraphStyle(
                'WrapStyle',
                parent=styles['Normal'],
                fontSize=8,
                leading=9
            )

            detail_data = [
                [Paragraph('REF', wrap_style),
                 Paragraph('Description', wrap_style),
                 Paragraph('Selling', wrap_style),
                 Paragraph('Cost', wrap_style)]
            ]

            for ref in refs:
                detail_data.append([
                    Paragraph(ref.ref_number or '', wrap_style),
                    Paragraph(ref.description or ref.detailed_description or '', wrap_style),
                    Paragraph(f"${float(ref.selling_price or 0):,.2f}", wrap_style),
                    Paragraph(f"${float(ref.cost_price or 0):,.2f}", wrap_style)
                ])

            # 总计行
            detail_data.append([
                Paragraph('TOTAL', wrap_style),
                Paragraph('', wrap_style),
                Paragraph(f"${total_selling:,.2f}", wrap_style),
                Paragraph(f"${total_cost:,.2f}", wrap_style)
            ])

            detail_table = Table(detail_data, colWidths=[1.5*inch, 4*inch, 1.5*inch, 1.5*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))

            story.append(detail_table)
            story.append(Spacer(1, 20))

            # 余额
            story.append(Paragraph(f"<b>Balance Due: ${balance:,.2f}</b>", styles['Normal']))
            story.append(Spacer(1, 20))

            # 银行信息
            bank_style = ParagraphStyle(
                'BankStyle',
                parent=styles['Normal'],
                fontSize=10,
                leading=12,
                alignment=TA_LEFT
            )

            story.append(Paragraph("<b>JOYFUL ESCAPES PTE. LTD Bank Details:</b>", bank_style))
            story.append(Paragraph("• OCBC Bank Singapore, AC No.: 5956-7793-1001", bank_style))
            story.append(Paragraph("• PayNow UEN: 202337627W", bank_style))
            story.append(Spacer(1, 20))

            story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))

            doc.build(story)
            buffer.seek(0)

            return buffer.getvalue(), None

        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, f"生成PDF时出错: {str(e)}"
