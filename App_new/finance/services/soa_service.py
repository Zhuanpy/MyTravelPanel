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

    def _get_project_departure_date(self, header_id):
        """从项目的第一个REF中获取出发日期"""
        try:
            first_ref = ProjectRef.query.filter_by(header_id=header_id).first()
            if first_ref and first_ref.extra_info:
                extra_data = json.loads(first_ref.extra_info)
                dep_date = extra_data.get('departure_date', '')
                if dep_date:
                    return dep_date
        except (json.JSONDecodeError, TypeError, Exception):
            pass
        return ''

    def get_soa_list(self, page=1, per_page=20, search=None, month=None, company=None, balance_positive=False, profit_loss=None):
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

            # 月份过滤
            if month:
                try:
                    year, month_num = month.split('-')
                    year = int(year)
                    month_num = int(month_num)

                    from datetime import date
                    start_date = date(year, month_num, 1)

                    if month_num == 12:
                        end_date = date(year + 1, 1, 1)
                    else:
                        end_date = date(year, month_num + 1, 1)

                    query = query.filter(
                        ProjectHeader.created_at >= start_date,
                        ProjectHeader.created_at < end_date
                    )
                except (ValueError, TypeError):
                    pass

            # 获取所有符合条件的项目（先不分页，因为需要计算余额后再过滤）
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

                # 从REF的extra_info获取出发日期
                dep_date = ''
                if first_ref and first_ref.extra_info:
                    try:
                        extra_data = json.loads(first_ref.extra_info)
                        dep_date = extra_data.get('departure_date', '')
                    except (json.JSONDecodeError, TypeError):
                        pass

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

    def get_company_list(self):
        """获取所有公司列表"""
        try:
            # 获取所有有项目的不重复公司名称
            companies = db.session.query(CustomerCompany.company_name).join(
                ProjectHeader, ProjectHeader.company_id == CustomerCompany.id
            ).filter(
                CustomerCompany.company_name.isnot(None),
                CustomerCompany.company_name != ''
            ).distinct().all()

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

    def batch_download_soa(self, company=None, month=None, search=None, balance_positive=None, profit_loss=None, format='excel'):
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

            if month:
                try:
                    year, month_num = month.split('-')
                    year = int(year)
                    month_num = int(month_num)

                    from datetime import date
                    start_date = date(year, month_num, 1)

                    if month_num == 12:
                        end_date = date(year + 1, 1, 1)
                    else:
                        end_date = date(year, month_num + 1, 1)

                    query = query.filter(
                        ProjectHeader.created_at >= start_date,
                        ProjectHeader.created_at < end_date
                    )
                except (ValueError, TypeError):
                    pass

            # 获取所有符合条件的项目
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

                # 从REF的extra_info获取出发日期
                dep_date = ''
                if first_ref and first_ref.extra_info:
                    try:
                        extra_data = json.loads(first_ref.extra_info)
                        dep_date = extra_data.get('departure_date', '')
                    except (json.JSONDecodeError, TypeError):
                        pass

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

            # 创建DataFrame
            df = pd.DataFrame(excel_data)

            # 计算BAL总数
            total_balance = df['BAL'].sum()

            # 添加总计行
            total_row = {
                'HID': '',
                'COMPANY': '',
                'BK.DATE': '',
                'CLIENT NAME': '',
                'DP.DATE': '',
                'ITIN DESCRIPTION': 'TOTAL',
                'CCY': '',
                'BAL': total_balance
            }

            df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

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

                # 设置总计行样式
                max_row = worksheet.max_row
                if max_row > 1:
                    total_row = worksheet[max_row]

                    total_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                    total_font = Font(bold=True, color="000080")

                    for cell in total_row:
                        cell.fill = total_fill
                        cell.font = total_font

                    if len(total_row) > 7:
                        total_row[7].number_format = '$#,##0.00'

                # 添加公司付款账户信息
                bank_info_start_row = max_row + 3

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

    def batch_download_soa_pdf(self, company=None, month=None, search=None, balance_positive=None, profit_loss=None):
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

            if month:
                try:
                    year, month_num = month.split('-')
                    year = int(year)
                    month_num = int(month_num)

                    from datetime import date
                    start_date = date(year, month_num, 1)

                    if month_num == 12:
                        end_date = date(year + 1, 1, 1)
                    else:
                        end_date = date(year, month_num + 1, 1)

                    query = query.filter(
                        ProjectHeader.created_at >= start_date,
                        ProjectHeader.created_at < end_date
                    )
                except (ValueError, TypeError):
                    pass

            # 获取所有符合条件的项目
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

            # 准备PDF数据
            pdf_data = []
            total_balance = 0

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

                total_balance += balance

                # 获取第一个REF的描述和出发日期
                first_ref = ProjectRef.query.filter_by(header_id=header.id).first()
                itin_desc = first_ref.description if first_ref and first_ref.description else header.desc

                # 从REF的extra_info获取出发日期
                dep_date = ''
                if first_ref and first_ref.extra_info:
                    try:
                        extra_data = json.loads(first_ref.extra_info)
                        dep_date = extra_data.get('departure_date', '')
                    except (json.JSONDecodeError, TypeError):
                        pass

                # 构建PDF行数据
                row_data = [
                    Paragraph(header.hid or '', batch_wrap_style),
                    Paragraph(header.company.company_name if header.company else '', batch_wrap_style),
                    Paragraph(header.created_at.strftime('%Y-%m-%d') if header.created_at else '', batch_wrap_style),
                    Paragraph(header.leader_member_name or header.leader_name or header.contact or '', batch_wrap_style),
                    Paragraph(dep_date, batch_wrap_style),  # DP.DATE
                    Paragraph(itin_desc or '', batch_wrap_style),
                    Paragraph('SGD', batch_wrap_style),
                    Paragraph(f"${balance:,.2f}", batch_wrap_style)
                ]

                pdf_data.append(row_data)

            if not pdf_data:
                return None, "没有找到符合条件的SOA数据"

            # 添加总计行
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

            total_row = [
                Paragraph('', total_wrap_style),
                Paragraph('', total_wrap_style),
                Paragraph('', total_wrap_style),
                Paragraph('', total_wrap_style),
                Paragraph('', total_wrap_style),
                Paragraph('TOTAL', total_wrap_style),
                Paragraph('', total_wrap_style),
                Paragraph(f"${total_balance:,.2f}", total_wrap_style)
            ]
            pdf_data.append(total_row)

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

            # 筛选条件说明
            filter_text = ""
            if company:
                filter_text = f"Company: {company}"
            elif month:
                filter_text = f"Month: {month}"
            else:
                filter_text = "All Data"

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

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#000080')),
            ])

            table.setStyle(table_style)
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
