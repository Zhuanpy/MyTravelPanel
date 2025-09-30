# -*- coding: utf-8 -*-
"""
SOA (Statement of Account) 生成服务
用于生成客户对账单
"""

from datetime import datetime
from App_new.exts import db
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
from flask import render_template, make_response
import io
import base64
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class SOAService:
    """SOA生成服务"""
    
    def __init__(self):
        pass
    
    def generate_soa_html(self, header_id):
        """生成HTML格式的SOA"""
        try:
            # 获取头部信息
            header = AthinaBookingHeader.query.get(header_id)
            if not header:
                return None, "Booking header record not found"
            
            # 获取明细记录
            details = AthinaBookingDetail.query.filter_by(header_id=header_id).order_by(
                AthinaBookingDetail.is_subtotal.desc(),  # 小计行在前
                AthinaBookingDetail.id.asc()
            ).all()
            
            # 当前日期时间
            current_date = datetime.now().strftime('%Y-%m-%d')
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return render_template(
                'finance/statement/athina/soa_template.html',
                header=header,
                details=details,
                current_date=current_date,
                current_datetime=current_datetime
            ), None
            
        except Exception as e:
            return None, f"Error generating SOA: {str(e)}"
    
    def generate_soa_pdf(self, header_id):
        """生成PDF格式的SOA"""
        try:
            # 获取头部信息
            header = AthinaBookingHeader.query.get(header_id)
            if not header:
                return None, "Booking header record not found"
            
            # 获取明细记录
            details = AthinaBookingDetail.query.filter_by(header_id=header_id).order_by(
                AthinaBookingDetail.is_subtotal.desc(),  # 小计行在前
                AthinaBookingDetail.id.asc()
            ).all()
            
            # 创建PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            
            # 获取样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            # 构建内容
            story = []
            
            # 标题
            story.append(Paragraph("Statement of Account", title_style))
            story.append(Spacer(1, 20))
            
            # 公司信息
            company_info = [
                ['Client Information', 'Statement Information'],
                [f'Company Name: {header.corporate_name or "N/A"}', f'Invoice No: {header.invoice_no or "N/A"}'],
                [f'Booking Ref: {header.booking_header_id}', f'Invoice Date: {header.invoice_date.strftime("%Y-%m-%d") if header.invoice_date else "N/A"}'],
                [f'Booking Date: {header.book_date.strftime("%Y-%m-%d") if header.book_date else "N/A"}', f'Generated Date: {datetime.now().strftime("%Y-%m-%d")}'],
                [f'Consultant: {header.consultant or "N/A"}', f'Currency: SGD'],
                [f'Sales Consultant: {header.sales_consultant or "N/A"}', '']
            ]
            
            # 优化公司信息表格列宽以匹配横版A4
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
            
            # 财务汇总
            story.append(Paragraph("Financial Summary", styles['Heading2']))
            
            summary_data = [
                ['Item', 'Amount (SGD)'],
                ['Gross Amount', f"{header.sub_total_gross or 0:.2f}"],
                ['Tax', f"{header.sub_total_tax or 0:.2f}"],
                ['Discount', f"{header.sub_total_discount or 0:.2f}"],
                ['Local Gross', f"{header.sub_total_local_gross or 0:.2f}"],
                ['Cost', f"{header.sub_total_cost or 0:.2f}"],
                ['Profit/Loss', f"{header.sub_total_pl or 0:.2f}"],
                ['Margin', f"{header.sub_total_margin or 0:.2f}%"],
                ['Balance', f"{header.sub_total_balance or 0:.2f}"]
            ]
            
            # 优化财务汇总表格列宽以匹配横版A4
            summary_table = Table(summary_data, colWidths=[5.5*inch, 3.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # 明细记录
            story.append(Paragraph("Transaction Details", styles['Heading2']))
            
            # 创建换行样式
            wrap_style = ParagraphStyle(
                'WrapStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=7,
                leading=8,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )
            
            detail_data = [
                [Paragraph('Client Name', wrap_style), 
                 Paragraph('Booking Ref', wrap_style), 
                 Paragraph('Type', wrap_style), 
                 Paragraph('Departure Date', wrap_style), 
                 Paragraph('Itinerary Description', wrap_style), 
                 Paragraph('Amount', wrap_style), 
                 Paragraph('Cost', wrap_style), 
                 Paragraph('Profit/Loss', wrap_style)]
            ]
            
            for detail in details:
                detail_data.append([
                    Paragraph(detail.client_name or 'N/A', wrap_style),
                    Paragraph(detail.booking_ref or 'N/A', wrap_style),
                    Paragraph(detail.book_type or 'N/A', wrap_style),
                    Paragraph(detail.dep_date.strftime('%Y-%m-%d') if detail.dep_date else 'N/A', wrap_style),
                    Paragraph(detail.itin_desc or 'N/A', wrap_style),
                    Paragraph(f"{detail.gross_amount or 0:.2f}", wrap_style),
                    Paragraph(f"{detail.local_cost or 0:.2f}", wrap_style),
                    Paragraph(f"{detail.profit_loss or 0:.2f}", wrap_style)
                ])
            
            # 优化列宽以匹配横版A4 (总宽度约10.5英寸)
            detail_table = Table(detail_data, colWidths=[0.8*inch, 1.85*inch, 0.7*inch, 1.0*inch, 1.85*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))
            
            story.append(detail_table)
            story.append(Spacer(1, 20))
            
            # Company Bank Information - Left aligned below table
            bank_style = ParagraphStyle(
                'BankStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=10,
                leading=12,
                leftIndent=0,
                alignment=TA_LEFT
            )
            
            story.append(Paragraph("<b>JOYFUL ESCAPES PTE. LTD Bank Details:</b>", bank_style))
            story.append(Paragraph("• OCBC Bank Singapore, AC No.: 5956-7793-1001", bank_style))
            story.append(Paragraph("• PayNow UEN: 202337627W", bank_style))
            story.append(Spacer(1, 20))
            
            # 页脚
            story.append(Paragraph("This statement is automatically generated by the system", styles['Normal']))
            story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            
            # 构建PDF
            doc.build(story)
            buffer.seek(0)
            
            return buffer.getvalue(), None
            
        except Exception as e:
            return None, f"Error generating PDF: {str(e)}"
    
    def get_soa_list(self, page=1, per_page=20, search=None, month=None, company=None):
        """获取可生成SOA的头部列表"""
        try:
            query = AthinaBookingHeader.query
            
            if search:
                query = query.filter(
                    AthinaBookingHeader.booking_header_id.contains(search) |
                    AthinaBookingHeader.corporate_name.contains(search)
                )
            
            # 公司过滤
            if company:
                query = query.filter(AthinaBookingHeader.corporate_name == company)
            
            # 月份过滤
            if month:
                # month格式: "2025-01" 或 "2025-1"
                try:
                    year, month_num = month.split('-')
                    year = int(year)
                    month_num = int(month_num)
                    
                    # 构建日期范围
                    from datetime import date
                    start_date = date(year, month_num, 1)
                    
                    # 计算下个月的第一天
                    if month_num == 12:
                        end_date = date(year + 1, 1, 1)
                    else:
                        end_date = date(year, month_num + 1, 1)
                    
                    # 过滤预订日期在指定月份内的记录
                    query = query.filter(
                        AthinaBookingHeader.book_date >= start_date,
                        AthinaBookingHeader.book_date < end_date
                    )
                except (ValueError, TypeError):
                    # 如果月份格式不正确，忽略过滤
                    pass
            
            pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 获取每个头部的第一个明细记录用于显示
            headers_data = []
            for header in pagination.items:
                # 获取第一个非小计明细记录
                first_detail = AthinaBookingDetail.query.filter_by(
                    header_id=header.id, 
                    is_subtotal=False
                ).first()
                
                headers_data.append({
                    'id': header.id,
                    'booking_header_id': header.booking_header_id,
                    'corporate_name': header.corporate_name,
                    'book_date': header.book_date.strftime('%Y-%m-%d') if header.book_date else None,
                    'client_name': first_detail.client_name if first_detail else None,
                    'dep_date': first_detail.dep_date.strftime('%Y-%m-%d') if first_detail and first_detail.dep_date else None,
                    'itin_desc': first_detail.itin_desc if first_detail else None,
                    'invoice_no': header.invoice_no,
                    'invoice_date': header.invoice_date.strftime('%Y-%m-%d') if header.invoice_date else None,
                    'sub_total_balance': float(header.sub_total_balance) if header.sub_total_balance else 0,
                    'detail_count': AthinaBookingDetail.query.filter_by(header_id=header.id).count()
                })
            
            return {
                'headers': headers_data,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get SOA list: {str(e)}'
            }
    
    def get_company_list(self):
        """获取所有公司列表"""
        try:
            # 获取所有不重复的公司名称
            companies = db.session.query(AthinaBookingHeader.corporate_name).filter(
                AthinaBookingHeader.corporate_name.isnot(None),
                AthinaBookingHeader.corporate_name != ''
            ).distinct().all()
            
            # 提取公司名称并过滤掉空值
            company_list = [company[0] for company in companies if company[0]]
            
            return {
                'success': True,
                'companies': company_list
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get company list: {str(e)}'
            }
    
    def batch_download_soa(self, company=None, month=None, format='excel'):
        """批量下载SOA - 生成Excel表格"""
        try:
            import pandas as pd
            import io
            from datetime import datetime
            
            # 构建查询条件
            query = AthinaBookingHeader.query
            
            if company:
                query = query.filter(AthinaBookingHeader.corporate_name == company)
            
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
                        AthinaBookingHeader.book_date >= start_date,
                        AthinaBookingHeader.book_date < end_date
                    )
                except (ValueError, TypeError):
                    pass
            
            # 获取所有符合条件的头部
            headers = query.all()
            
            if not headers:
                return None, "No SOA data found matching the criteria"
            
            # 准备Excel数据 - 只包含指定字段，每个HID只取第一个ref的详细信息
            excel_data = []
            
            for header in headers:
                # 获取该头部的第一个非小计明细记录
                first_detail = AthinaBookingDetail.query.filter_by(header_id=header.id).filter(
                    AthinaBookingDetail.is_subtotal == False
                ).order_by(AthinaBookingDetail.id.asc()).first()
                
                # 构建Excel行数据
                row_data = {
                    'HID': header.booking_header_id,
                    'COMPANY': header.corporate_name or '',
                    'BK.DATE': first_detail.book_date.strftime('%Y-%m-%d') if first_detail and first_detail.book_date else '',
                    'CLIENT NAME': first_detail.client_name or '' if first_detail else '',
                    'DP.DATE': first_detail.dep_date.strftime('%Y-%m-%d') if first_detail and first_detail.dep_date else '',
                    'ITIN DESCRIPTION': first_detail.itin_desc or '' if first_detail else '',
                    'CCY': 'SGD',
                    'BAL': float(header.sub_total_balance) if header.sub_total_balance else 0
                }
                
                excel_data.append(row_data)
            
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
            
            # 将总计行添加到DataFrame
            df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
            
            # 生成Excel文件
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='SOA Data', index=False)
                
                # 获取工作表对象以进行格式化
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
                from openpyxl.styles import NamedStyle
                currency_style = NamedStyle(name="currency")
                currency_style.number_format = '$#,##0.00'
                
                for row in worksheet.iter_rows(min_row=2):
                    # Set BAL column currency format (H column: BAL)
                    if len(row) > 7:  # 确保H列存在
                        row[7].number_format = '$#,##0.00'  # H column (index 7)
                
                # 设置总计行样式
                # 获取总行数（包括表头）
                max_row = worksheet.max_row
                if max_row > 1:  # 确保有数据行
                    total_row_num = max_row
                    total_row = worksheet[total_row_num]
                    
                    # 设置总计行背景色和字体
                    from openpyxl.styles import PatternFill, Font
                    total_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                    total_font = Font(bold=True, color="000080")
                    
                    for cell in total_row:
                        cell.fill = total_fill
                        cell.font = total_font
                    
                    # 特别设置BAL列的格式
                    if len(total_row) > 7:
                        total_row[7].number_format = '$#,##0.00'
            
            excel_buffer.seek(0)
            return excel_buffer.getvalue(), None
            
        except Exception as e:
            return None, f"Error generating Excel file: {str(e)}"
    
    def batch_download_soa_pdf(self, company=None, month=None):
        """批量下载SOA - 生成PDF文件"""
        try:
            # 构建查询条件
            query = AthinaBookingHeader.query
            
            if company:
                query = query.filter(AthinaBookingHeader.corporate_name == company)
            
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
                        AthinaBookingHeader.book_date >= start_date,
                        AthinaBookingHeader.book_date < end_date
                    )
                except (ValueError, TypeError):
                    pass
            
            # 获取所有符合条件的头部
            headers = query.all()
            
            if not headers:
                return None, "No SOA data found matching the criteria"
            
            # 准备PDF数据 - 与Excel保持一致
            pdf_data = []
            
            for header in headers:
                # 获取该头部的第一个非小计明细记录
                first_detail = AthinaBookingDetail.query.filter_by(header_id=header.id).filter(
                    AthinaBookingDetail.is_subtotal == False
                ).order_by(AthinaBookingDetail.id.asc()).first()
                
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
                
                # 构建PDF行数据
                row_data = [
                    Paragraph(header.booking_header_id or '', batch_wrap_style),
                    Paragraph(header.corporate_name or '', batch_wrap_style),
                    Paragraph(first_detail.book_date.strftime('%Y-%m-%d') if first_detail and first_detail.book_date else '', batch_wrap_style),
                    Paragraph(first_detail.client_name or '' if first_detail else '', batch_wrap_style),
                    Paragraph(first_detail.dep_date.strftime('%Y-%m-%d') if first_detail and first_detail.dep_date else '', batch_wrap_style),
                    Paragraph(first_detail.itin_desc or '' if first_detail else '', batch_wrap_style),
                    Paragraph('SGD', batch_wrap_style),
                    Paragraph(f"${float(header.sub_total_balance):,.2f}" if header.sub_total_balance else '$0.00', batch_wrap_style)
                ]
                
                pdf_data.append(row_data)
            
            # 计算BAL总数
            total_balance = sum(float(header.sub_total_balance) if header.sub_total_balance else 0 for header in headers)
            
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
            
            # 创建样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            # 构建PDF内容
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
            
            # 创建表格 - 优化列宽以匹配横版A4
            table = Table(table_data, colWidths=[0.6*inch, 1.85*inch, 0.8*inch, 1.5*inch, 0.8*inch, 1.85*inch, 0.6*inch, 0.8*inch])
            
            # 设置表格样式
            table_style = TableStyle([
                # 表头样式
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # 数据行样式
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                
                # 总计行样式
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#000080')),
            ])
            
            table.setStyle(table_style)
            story.append(table)
            
            # Company Bank Information - Left aligned below table
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
            
            # 生成PDF
            doc.build(story)
            pdf_buffer.seek(0)
            
            return pdf_buffer.getvalue(), None
            
        except Exception as e:
            return None, f"Error generating PDF file: {str(e)}"
