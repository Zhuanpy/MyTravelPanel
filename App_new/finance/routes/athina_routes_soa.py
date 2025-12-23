# -*- coding: utf-8 -*-
"""
SOA 相关路由 - 单独文件
"""

from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, make_response, current_app
from flask_login import login_required
from App_new.exts import csrf, db
from App_new.utils.decorators import staff_only
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
from App_new.finance.services.soa_service import SOAService
from datetime import datetime

# 创建 SOA 蓝图
soa_blue = Blueprint('soa_routes', __name__)


@soa_blue.route('/soa_list')
@login_required
@staff_only
def soa_list():
    """SOA列表页面"""
    return render_template('finance/athina/soa_list.html')


@soa_blue.route('/soa_data')
@login_required
@staff_only
def soa_data():
    """获取SOA数据列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        month = request.args.get('month', '')
        company = request.args.get('company', '')
        balance_positive = request.args.get('balance_positive', 'false').lower() == 'true'
        
        soa_service = SOAService()
        result = soa_service.get_soa_list(page=page, per_page=per_page, search=search, month=month, company=company, balance_positive=balance_positive)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@soa_blue.route('/soa_companies')
@login_required
@staff_only
def soa_companies():
    """获取公司列表"""
    try:
        soa_service = SOAService()
        result = soa_service.get_company_list()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@soa_blue.route('/soa_batch_download')
@login_required
@staff_only
def soa_batch_download():
    """批量下载SOA - Excel表格"""
    try:
        company = request.args.get('company', '')
        month = request.args.get('month', '')
        search = request.args.get('search', '')
        balance_positive = request.args.get('balance_positive', 'false').lower() == 'true'
        format_type = request.args.get('format', 'excel')
        
        # 记录请求参数用于调试
        current_app.logger.info(f"SOA批量下载请求 - 公司: {company}, 月份: {month}, 搜索: {search}, 余额正: {balance_positive}, 格式: {format_type}")
        
        soa_service = SOAService()
        excel_content, error = soa_service.batch_download_soa(
            company=company if company else None,
            month=month if month else None,
            search=search if search else None,
            balance_positive=balance_positive,
            format=format_type
        )
        
        if error or excel_content is None:
            # 返回错误信息而不是重定向
            error_msg = error or "没有找到匹配的SOA数据"
            current_app.logger.error(f"SOA批量下载失败: {error_msg}")
            # 确保返回 JSON 格式的错误响应
            response = jsonify({'success': False, 'message': f'批量下载失败: {error_msg}'})
            response.status_code = 400
            return response
        
        # 生成文件名
        filename_parts = []
        if company:
            filename_parts.append(company.replace(' ', '_'))
        if month:
            filename_parts.append(month)
        filename_parts.append(datetime.now().strftime('%Y%m%d'))
        
        filename = f"SOA_{'_'.join(filename_parts)}.xlsx"
        
        # 确保 excel_content 不为空
        if not excel_content:
            current_app.logger.error("生成的Excel内容为空")
            return jsonify({'success': False, 'message': '生成的Excel文件为空'}), 400
        
        response = make_response(excel_content)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        current_app.logger.info(f"SOA批量下载成功: {filename}")
        return response
        
    except Exception as e:
        # 记录完整的错误堆栈
        current_app.logger.exception(f"SOA批量下载异常: {str(e)}")
        # 返回错误信息而不是重定向
        return jsonify({'success': False, 'message': f'批量下载时出错: {str(e)}'}), 500


@soa_blue.route('/soa_batch_download_pdf')
@login_required
@staff_only
def soa_batch_download_pdf():
    """批量下载SOA PDF"""
    try:
        company = request.args.get('company', '')
        month = request.args.get('month', '')
        search = request.args.get('search', '')
        balance_positive = request.args.get('balance_positive', 'false').lower() == 'true'
        
        # 记录请求参数用于调试
        current_app.logger.info(f"SOA批量下载PDF请求 - 公司: {company}, 月份: {month}, 搜索: {search}, 余额正: {balance_positive}")
        
        soa_service = SOAService()
        pdf_content, error = soa_service.batch_download_soa_pdf(
            company=company if company else None,
            month=month if month else None,
            search=search if search else None,
            balance_positive=balance_positive
        )
        
        if error or pdf_content is None:
            # 返回错误信息而不是重定向
            error_msg = error or "没有找到匹配的SOA数据"
            current_app.logger.error(f"SOA批量下载PDF失败: {error_msg}")
            # 确保返回 JSON 格式的错误响应
            response = jsonify({'success': False, 'message': f'批量下载PDF失败: {error_msg}'})
            response.status_code = 400
            return response
        
        # 生成文件名
        filename_parts = []
        if company:
            filename_parts.append(company.replace(' ', '_'))
        if month:
            filename_parts.append(month)
        filename_parts.append(datetime.now().strftime('%Y%m%d'))
        
        filename = f"SOA_{'_'.join(filename_parts)}.pdf"
        
        # 确保 pdf_content 不为空
        if not pdf_content:
            current_app.logger.error("生成的PDF内容为空")
            return jsonify({'success': False, 'message': '生成的PDF文件为空'}), 400
        
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        current_app.logger.info(f"SOA批量下载PDF成功: {filename}")
        return response
        
    except Exception as e:
        # 记录完整的错误堆栈
        current_app.logger.exception(f"SOA批量下载PDF异常: {str(e)}")
        # 返回错误信息而不是重定向
        return jsonify({'success': False, 'message': f'批量下载PDF时出错: {str(e)}'}), 500


@soa_blue.route('/soa_preview/<int:header_id>')
@login_required
@staff_only
def soa_preview(header_id):
    """预览SOA"""
    try:
        soa_service = SOAService()
        html_content, error = soa_service.generate_soa_html(header_id)
        
        if error:
            flash(f'生成SOA预览失败: {error}', 'error')
            return redirect(url_for('soa_routes.soa_list'))
        
        return html_content
        
    except Exception as e:
        flash(f'预览SOA时出错: {str(e)}', 'error')
        return redirect(url_for('soa_routes.soa_list'))


@soa_blue.route('/soa_download/<int:header_id>')
@login_required
@staff_only
def soa_download(header_id):
    """下载SOA PDF"""
    try:
        soa_service = SOAService()
        pdf_content, error = soa_service.generate_soa_pdf(header_id)
        
        if error:
            flash(f'生成SOA PDF失败: {error}', 'error')
            return redirect(url_for('soa_routes.soa_list'))
        
        # 获取头部信息用于文件名
        header = AthinaBookingHeader.query.get(header_id)
        filename = f"SOA_{header.booking_header_id}_{header.corporate_name or 'Unknown'}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # 清理文件名中的特殊字符
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        flash(f'下载SOA时出错: {str(e)}', 'error')
        return redirect(url_for('soa_routes.soa_list'))


@soa_blue.route('/soa_download_html/<int:header_id>')
@login_required
@staff_only
def soa_download_html(header_id):
    """下载SOA HTML"""
    try:
        soa_service = SOAService()
        html_content, error = soa_service.generate_soa_html(header_id)
        
        if error:
            flash(f'生成SOA HTML失败: {error}', 'error')
            return redirect(url_for('soa_routes.soa_list'))
        
        # 获取头部信息用于文件名
        header = AthinaBookingHeader.query.get(header_id)
        filename = f"SOA_{header.booking_header_id}_{header.corporate_name or 'Unknown'}_{datetime.now().strftime('%Y%m%d')}.html"
        
        # 清理文件名中的特殊字符
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        flash(f'下载SOA HTML时出错: {str(e)}', 'error')
        return redirect(url_for('soa_routes.soa_list'))
