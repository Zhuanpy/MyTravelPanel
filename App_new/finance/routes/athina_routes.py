# -*- coding: utf-8 -*-
"""Athina 相关路由"""

from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, send_file
from io import BytesIO
from flask_login import login_required, current_user
from App_new.exts import csrf, db
from App_new.utils.decorators import staff_only
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail
from App_new.utils.report_utils import get_report_headers_string
from App_new.finance.services.soa_service import SOAService
from datetime import datetime
import os
import tempfile
import pandas as pd
import logging
from openpyxl.utils import get_column_letter

# 创建logger
logger = logging.getLogger(__name__)

# 创建 Athina 蓝图
athina_blue = Blueprint('athina_routes', __name__)


@athina_blue.route('/athina_page')
@login_required
@staff_only
def athina_page():
    """Athina 主页面"""
    return render_template('finance/athina/athina.html')


@athina_blue.route('/athina_import')
@login_required
@staff_only
def athina_import():
    """Athina数据录入页面"""
    return render_template('finance/athina/athina_import.html')


@athina_blue.route('/athina_analysis')
@login_required
@staff_only
def athina_analysis():
    """Athina分析报表页面"""
    return render_template('finance/athina/athina_analysis.html')


@athina_blue.route('/athina_import_csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_csv():
    """导入Athina CSV文件"""
    try:
        from App_new.finance.services.athina_import_service import AthinaImportService
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({
                'success': False,
                'message': '请选择CSV格式的文件'
            }), 400
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name
        
        try:
            # 导入CSV文件
            import_service = AthinaImportService()
            result = import_service.import_csv_file(tmp_file_path)
            
            return jsonify(result)
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Athina导入错误: {str(e)}")
        print(f"错误详情: {error_details}")
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}',
            'error_details': error_details
        }), 500


@athina_blue.route('/athina_stats')
@login_required
@staff_only
def athina_stats():
    """获取Athina数据统计"""
    try:
        total_headers = AthinaBookingHeader.query.count()
        total_details = AthinaBookingDetail.query.count()
        
        # 获取最后导入时间
        last_header = AthinaBookingHeader.query.order_by(AthinaBookingHeader.created_at.desc()).first()
        last_import = last_header.created_at.strftime('%Y-%m-%d %H:%M') if last_header else '-'
        
        return jsonify({
            'success': True,
            'total_headers': total_headers,
            'total_details': total_details,
            'last_import': last_import
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_header_data')
@login_required
@staff_only
def athina_header_data():
    """Athina数据查看页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        # 筛选参数
        filter_corporate_name = request.args.get('filter_corporate_name', '')
        filter_consultant = request.args.get('filter_consultant', '')
        filter_sales_consultant = request.args.get('filter_sales_consultant', '')
        filter_is_all_invoiced = request.args.get('filter_is_all_invoiced', '')
        filter_is_count_performance = request.args.get('filter_is_count_performance', '')
        filter_pl = request.args.get('filter_pl', '')  # 'negative': 小于0, 'zero': 等于0, 'positive': 大于0
        filter_book_date_from = request.args.get('filter_book_date_from', '')
        filter_book_date_to = request.args.get('filter_book_date_to', '')
        filter_dep_date_from = request.args.get('filter_dep_date_from', '')
        filter_dep_date_to = request.args.get('filter_dep_date_to', '')
        
        # 构建查询
        query = AthinaBookingHeader.query
        
        # 先应用所有对header表直接的筛选条件（不需要join的）
        if filter_corporate_name:
            query = query.filter(AthinaBookingHeader.corporate_name.contains(filter_corporate_name))
        
        if filter_consultant:
            query = query.filter(AthinaBookingHeader.consultant.contains(filter_consultant))
        
        if filter_sales_consultant:
            query = query.filter(AthinaBookingHeader.sales_consultant.contains(filter_sales_consultant))
        
        if filter_is_all_invoiced != '':
            is_invoiced = filter_is_all_invoiced.lower() == 'true'
            query = query.filter(AthinaBookingHeader.is_all_invoiced == is_invoiced)
        
        if filter_is_count_performance != '':
            is_count_perf = filter_is_count_performance.lower() == 'true'
            query = query.filter(AthinaBookingHeader.is_count_performance == is_count_perf)
        
        # 盈亏筛选 - 在join之前应用，确保条件正确
        if filter_pl != '':
            query = query.filter(AthinaBookingHeader.sub_total_pl.isnot(None))
            if filter_pl == 'negative':
                # 筛选盈亏小于0的记录
                query = query.filter(AthinaBookingHeader.sub_total_pl < 0)
            elif filter_pl == 'zero':
                # 筛选盈亏等于0的记录
                query = query.filter(AthinaBookingHeader.sub_total_pl == 0)
            elif filter_pl == 'positive':
                # 筛选盈亏大于0的记录
                query = query.filter(AthinaBookingHeader.sub_total_pl > 0)
        
        if filter_book_date_from:
            query = query.filter(AthinaBookingHeader.book_date >= filter_book_date_from)
        
        if filter_book_date_to:
            query = query.filter(AthinaBookingHeader.book_date <= filter_book_date_to)
        
        # 需要join的筛选条件（search和dep_date）
        needs_distinct = False
        
        if search:
            # 搜索时需要关联detail表来搜索client_name等字段
            query = query.outerjoin(AthinaBookingDetail).filter(
                db.or_(
                    AthinaBookingHeader.booking_header_id.contains(search),
                    AthinaBookingHeader.corporate_name.contains(search),
                    AthinaBookingDetail.client_name.contains(search),
                    AthinaBookingDetail.booking_ref.cast(db.String).contains(search),
                    AthinaBookingDetail.supplier.contains(search)
                )
            )
            needs_distinct = True
        
        if filter_dep_date_from or filter_dep_date_to:
            # 出发日期在detail表中，需要关联查询
            if not search:  # 如果search已经做了join，就不需要再join了
                query = query.outerjoin(AthinaBookingDetail)
            query = query.filter(
                AthinaBookingDetail.is_subtotal == False
            )
            if filter_dep_date_from:
                query = query.filter(AthinaBookingDetail.dep_date >= filter_dep_date_from)
            if filter_dep_date_to:
                query = query.filter(AthinaBookingDetail.dep_date <= filter_dep_date_to)
            needs_distinct = True
        
        # 如果有join，需要distinct去重
        if needs_distinct:
            query = query.distinct()
        
        query = query.order_by(AthinaBookingHeader.created_at.desc())
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # 为每个header添加来自第一个detail的信息
        headers_with_details = []
        for header in pagination.items:
            # 更新开票状态
            header.update_invoice_status()
            
            # 获取第一个非小计的明细记录
            first_detail = AthinaBookingDetail.query.filter_by(
                header_id=header.id, 
                is_subtotal=False
            ).first()
            
            # 创建一个包含header和detail信息的对象
            # 客户名称直接使用header的corporate_name字段
            header.booking_ref = first_detail.booking_ref if first_detail else None
            header.book_type = first_detail.book_type if first_detail else None
            header.dep_date = first_detail.dep_date if first_detail else None
            header.gross_amount = header.sub_total_gross
            header.margin = header.sub_total_margin
            header.supplier = first_detail.supplier if first_detail else None
            
            headers_with_details.append(header)
        
        # 批量提交状态更新
        db.session.commit()
        
        # 获取唯一的顾问列表用于下拉选择
        consultants = db.session.query(AthinaBookingHeader.consultant).distinct().filter(
            AthinaBookingHeader.consultant.isnot(None),
            AthinaBookingHeader.consultant != ''
        ).order_by(AthinaBookingHeader.consultant).all()
        consultants = [c[0] for c in consultants]
        
        sales_consultants = db.session.query(AthinaBookingHeader.sales_consultant).distinct().filter(
            AthinaBookingHeader.sales_consultant.isnot(None),
            AthinaBookingHeader.sales_consultant != ''
        ).order_by(AthinaBookingHeader.sales_consultant).all()
        sales_consultants = [c[0] for c in sales_consultants]
        
        # 获取唯一的公司名称列表
        corporate_names = db.session.query(AthinaBookingHeader.corporate_name).distinct().filter(
            AthinaBookingHeader.corporate_name.isnot(None),
            AthinaBookingHeader.corporate_name != ''
        ).order_by(AthinaBookingHeader.corporate_name).all()
        corporate_names = [c[0] for c in corporate_names]
        
        return render_template('finance/athina/athina_data.html', 
                             headers=headers_with_details,
                             pagination=pagination,
                             search=search,
                             filter_corporate_name=filter_corporate_name,
                             filter_consultant=filter_consultant,
                             filter_sales_consultant=filter_sales_consultant,
                             filter_is_all_invoiced=filter_is_all_invoiced,
                             filter_is_count_performance=filter_is_count_performance,
                             filter_pl=filter_pl,
                             filter_book_date_from=filter_book_date_from,
                             filter_book_date_to=filter_book_date_to,
                             filter_dep_date_from=filter_dep_date_from,
                             filter_dep_date_to=filter_dep_date_to,
                             consultants=consultants,
                             sales_consultants=sales_consultants,
                             corporate_names=corporate_names)
        
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'error')
        return redirect(url_for('athina_routes.athina_import'))


@athina_blue.route('/athina_clear_data', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_clear_data():
    """清空Athina数据"""
    try:
        # 删除所有数据
        AthinaBookingDetail.query.delete()
        AthinaBookingHeader.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '数据已清空'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'清空失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_recalculate_subtotals', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_recalculate_subtotals():
    """重新计算所有Sub Total数据"""
    try:
        from App_new.finance.services.athina_import_service import AthinaImportService
        
        service = AthinaImportService()
        result = service.recalculate_all_subtotals()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'重新计算失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_toggle_performance/<int:header_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_toggle_performance(header_id):
    """切换是否算业绩状态"""
    try:
        header = AthinaBookingHeader.query.get_or_404(header_id)
        header.is_count_performance = not header.is_count_performance
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_count_performance': header.is_count_performance,
            'message': '状态已更新'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_update_consultants/<int:header_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_update_consultants(header_id):
    """更新操作顾问和销售顾问"""
    try:
        header = AthinaBookingHeader.query.get_or_404(header_id)
        
        # 检查是否已核算业绩，如果已核算则不允许编辑
        if header.is_count_performance:
            return jsonify({
                'success': False,
                'message': '该记录已核算业绩，不允许修改顾问信息'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据为空'
            }), 400
        
        consultant = data.get('consultant', '').strip() if data.get('consultant') else None
        sales_consultant = data.get('sales_consultant', '').strip() if data.get('sales_consultant') else None
        
        # 更新顾问信息（只更新传入的字段）
        if 'consultant' in data:
            header.consultant = consultant if consultant else None
        if 'sales_consultant' in data:
            header.sales_consultant = sales_consultant if sales_consultant else None
        
        header.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'consultant': header.consultant or '',
            'sales_consultant': header.sales_consultant or '',
            'message': '顾问信息已更新'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        logger.error(f'更新顾问信息失败: {str(e)}\n{error_details}')
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_delete_header/<int:header_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_delete_header(header_id):
    """删除单个Athina预订头部及其明细"""
    try:
        header = AthinaBookingHeader.query.get_or_404(header_id)
        db.session.delete(header)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'预订头部 {header_id} 及其明细已删除'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_detail/<int:header_id>')
@login_required
@staff_only
def athina_detail(header_id):
    """Athina预订详情页面"""
    try:
        # 获取预订头部信息
        header = AthinaBookingHeader.query.get_or_404(header_id)
        
        # 更新开票状态
        header.update_invoice_status()
        db.session.commit()
        
        # 获取明细记录
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        details_query = AthinaBookingDetail.query.filter_by(header_id=header_id)
        details_query = details_query.order_by(AthinaBookingDetail.id.asc())
        
        pagination = details_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return render_template('finance/athina/athina_detail.html', 
                             header=header,
                             details=pagination.items,
                             pagination=pagination)
        
    except Exception as e:
        flash(f'加载详情失败: {str(e)}', 'error')
        return redirect(url_for('athina_routes.athina_header_data'))


@athina_blue.route('/athina_processing', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@staff_only
def process_all_invoices():
    """处理全部订单"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始处理全部订单计算请求")
        
        from App_new.utils.Invoice import CountHid
        from App_new.config import Config
        from pathlib import Path
        
        # 初始化CountHid类
        booking_path = Path(Config.BILLING_DATA_PATH) / "BOOKING"
        logger.info(f"账单路径: {booking_path}")
        
        if not booking_path.exists():
            error_msg = f'账单路径不存在: {booking_path}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 404
        
        # 检查子目录
        zz_path = booking_path / "Zz"
        if not zz_path.exists():
            error_msg = f'Zz文件夹不存在: {zz_path}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 404
        
        logger.info("创建CountHid实例")
        # 创建CountHid实例
        count_hid = CountHid(str(booking_path), name="Zz")
        
        logger.info("开始计算未结算订单")
        # 计算未结算订单
        # 返回值：(complete_month之后的总利润, 已结算利润)
        total_profit, settled_profit = count_hid.find_no_inv_booking()
        unsettled_profit = total_profit - settled_profit
        
        logger.info(f"计算完成 - 总利润: {total_profit}, 已结算: {settled_profit}, 未结算: {unsettled_profit}")
        
        # 格式化结果信息
        complete_month_str = str(count_hid._get_complete_month())
        complete_month_display = f"{complete_month_str[:4]}-{complete_month_str[4:]}" if len(complete_month_str) == 6 else complete_month_str
        
        result_info = f"""
📊 业绩结算统计报告

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 {complete_month_display} 之后的利润汇总
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 总业绩（{complete_month_display}之后）: ${total_profit:,.2f}
   ├─ ✅ 已结算利润: ${settled_profit:,.2f} ({settled_profit/total_profit*100:.1f}%)
   └─ ⏳ 未结算利润: ${unsettled_profit:,.2f} ({unsettled_profit/total_profit*100:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• 总业绩: {complete_month_display} 之后所有HID订单的利润总和
• 已结算: 公司已开具Invoice的订单利润
• 未结算: 尚未开具Invoice的订单利润（需要追踪）
• 已排除: disputed.txt 中标记的争议订单

💡 做账进度: 
• complete.txt 当前值: {complete_month_display}
• 表示此月份之前的订单已核对完成
• 如需查看更早月份，请修改 complete.txt 为更早日期
"""
        
        # 获取未结算订单的详细数据（可选）
        # unsettled_orders = count_hid.get_unsettled_orders()  # 如果需要详细列表，可以添加这个方法
        
        return jsonify({
            'result': result_info.strip(),
            'total_profit': total_profit,
            'settled_profit': settled_profit,
            'unsettled_profit': unsettled_profit,
            'summary': {
                'total_profit': float(total_profit),
                'settled_profit': float(settled_profit),
                'unsettled_profit': float(unsettled_profit),
                'complete_month': complete_month_display
            }
        })
        
    except FileNotFoundError as e:
        error_msg = f'路径错误: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': error_msg}), 404
    except Exception as e:
        error_msg = f'处理失败: {str(e)}'
        logger.error(error_msg, exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@athina_blue.route('/athina_processing_month', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def process_month_invoice():
    """处理指定月份订单"""
    import logging
    import re
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始处理指定月份订单计算请求")
        
        from App_new.utils.Invoice import CountHid
        from App_new.config import Config
        from pathlib import Path
        
        # 获取请求中的月份参数
        data = request.get_json()
        month = data.get('month', '')  # 格式: YYYY-MM
        
        logger.info(f"请求月份: {month}")
        
        if not month:
            error_msg = '请提供月份参数'
            logger.warning(error_msg)
            return jsonify({'error': error_msg}), 400
        
        # 验证月份格式
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', month):
            error_msg = '月份格式错误，应为 YYYY-MM'
            logger.warning(f"{error_msg}, 实际输入: {month}")
            return jsonify({'error': error_msg}), 400
        
        # 初始化CountHid类
        booking_path = Path(Config.BILLING_DATA_PATH) / "BOOKING"
        logger.info(f"账单路径: {booking_path}")
        
        if not booking_path.exists():
            error_msg = f'账单路径不存在: {booking_path}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 404
        
        # 检查子目录
        zz_path = booking_path / "Zz"
        if not zz_path.exists():
            error_msg = f'Zz文件夹不存在: {zz_path}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 404
        
        logger.info("创建CountHid实例")
        # 创建CountHid实例
        count_hid = CountHid(str(booking_path), name="Zz")
        
        logger.info(f"开始计算 {month} 月份的未结算订单")
        # 计算指定月份之前的未结算订单
        total_profit, pre_profit = count_hid.find_no_inv_booking(pre_month=month)
        
        # 计算当前月份的利润
        current_month_profit = total_profit - pre_profit
        
        logger.info(f"{month} 月份计算完成 - 总利润: {total_profit}, 前期利润: {pre_profit}, 当前: {current_month_profit}")
        
        # 格式化结果
        result = f"""📊 {month} 月份订单计算完成

总利润: ${total_profit:,.2f}
{month} 之前利润: ${pre_profit:,.2f}
{month} 当前利润: ${current_month_profit:,.2f}"""
        
        return jsonify({
            'result': result,
            'month': month,
            'total_profit': total_profit,
            'pre_profit': pre_profit,
            'current_month_profit': current_month_profit
        })
        
    except FileNotFoundError as e:
        error_msg = f'路径错误: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': error_msg}), 404
    except Exception as e:
        error_msg = f'处理失败: {str(e)}'
        logger.error(error_msg, exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@athina_blue.route('/open_athina_statement_folder', methods=['GET', 'POST'])
@csrf.exempt
def open_athina_statement_folder():
    """打开Athina账单文件夹"""
    from App_new.config import Config
    from pathlib import Path
    
    folder_path = Path(Config.BILLING_DATA_PATH) / "BOOKING"
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash('文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect(url_for("athina_routes.athina_page"))
    
    try:
        os.startfile(str(folder_path))
        flash('成功打开BOOKING文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("athina_routes.athina_page"))


@athina_blue.route('/compare_reports', methods=['POST'])
@csrf.exempt
def compare_reports():
    """对比两个报表的利润列数据"""
    try:
        print("=== 开始处理报表对比请求 ===")
        
        # 获取上传的文件
        report_a = request.files.get('report_a')
        report_b = request.files.get('report_b')
        profit_column = request.form.get('profit_column', '').strip()
        header_setting = request.form.get('header_setting', 'default')
        custom_headers = request.form.get('custom_headers', '').strip()
        
        # 如果没有提供自定义表头，使用config中的默认表头
        if not custom_headers:
            custom_headers = get_report_headers_string('order_report')
        
        print(f"Debug: report_a filename = {report_a.filename if report_a else 'None'}")
        print(f"Debug: report_b filename = {report_b.filename if report_b else 'None'}")
        print(f"Debug: profit_column = {profit_column}")
        print(f"Debug: header_setting = {header_setting}")
        print(f"Debug: custom_headers = {custom_headers}")
        
        # 检查请求参数
        print(f"Debug: request.files keys = {list(request.files.keys())}")
        print(f"Debug: request.form keys = {list(request.form.keys())}")
        
        if not report_a or not report_b:
            return jsonify({'success': False, 'error': '请选择两个报表文件'})
        
        # 读取报表文件
        def read_report_file(file, header_setting, custom_headers=None):
            """读取Excel或CSV文件"""
            try:
                print(f"Debug: 读取文件 {file.filename}, header_setting={header_setting}")
                
                if file.filename.lower().endswith('.csv'):
                    if header_setting == 'none':
                        # 无表头，第一行是数据
                        df = pd.read_csv(file, encoding='utf-8', header=None)
                    elif header_setting == 'custom' and custom_headers:
                        # 使用自定义表头
                        headers = [h.strip() for h in custom_headers.split(',')]
                        df = pd.read_csv(file, encoding='utf-8', header=None, names=headers)
                    else:
                        # 使用默认表头（第一行作为表头）
                        df = pd.read_csv(file, encoding='utf-8')
                else:
                    # 处理Excel文件（.xlsx, .xls）
                    if header_setting == 'custom' and custom_headers:
                        # 使用自定义表头
                        headers = [h.strip() for h in custom_headers.split(',')]
                        print(f"Debug: 使用自定义表头: {headers}")
                        # 尝试不同的引擎
                        try:
                            df = pd.read_excel(file, header=None, names=headers, engine='openpyxl')
                        except:
                            try:
                                df = pd.read_excel(file, header=None, names=headers, engine='xlrd')
                            except:
                                # 最后尝试不指定引擎
                                df = pd.read_excel(file, header=None, names=headers)
                    else:
                        # 使用默认表头（第一行作为表头）
                        try:
                            df = pd.read_excel(file, engine='openpyxl')
                        except:
                            try:
                                df = pd.read_excel(file, engine='xlrd')
                            except:
                                # 最后尝试不指定引擎
                                df = pd.read_excel(file)
                return df
            except Exception as e:
                print(f"Debug: 文件读取最终失败: {str(e)}")
                raise Exception(f"读取文件失败: {str(e)}")
        
        # 读取两个报表
        print(f"Debug: 开始读取报表A...")
        df_a = read_report_file(report_a, header_setting, custom_headers)
        print(f"Debug: 报表A读取成功，列数: {len(df_a.columns)}, 行数: {len(df_a)}")
        print(f"Debug: 报表A列名: {list(df_a.columns)}")
        
        print(f"Debug: 开始读取报表B...")
        df_b = read_report_file(report_b, header_setting, custom_headers)
        print(f"Debug: 报表B读取成功，列数: {len(df_b.columns)}, 行数: {len(df_b)}")
        print(f"Debug: 报表B列名: {list(df_b.columns)}")
        
        # 检查利润列是否存在
        if profit_column not in df_a.columns:
            return jsonify({'success': False, 'error': f'报表A中未找到列: {profit_column}'})
        
        if profit_column not in df_b.columns:
            return jsonify({'success': False, 'error': f'报表B中未找到列: {profit_column}'})
        
        # 获取项目标识列（假设第一列是项目标识）
        id_column_a = df_a.columns[0]
        id_column_b = df_b.columns[0]
        
        # 创建数据字典，以项目标识为键
        data_a = {}
        data_b = {}
        
        # 处理报表A
        for _, row in df_a.iterrows():
            item_id = str(row[id_column_a]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):  # 排除空值
                try:
                    # 尝试转换为浮点数
                    float_value = float(profit_value)
                    data_a[item_id] = float_value
                except (ValueError, TypeError):
                    # 如果转换失败，记录警告并跳过
                    print(f"警告：报表A中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    continue
        
        # 处理报表B
        for _, row in df_b.iterrows():
            item_id = str(row[id_column_b]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):  # 排除空值
                try:
                    # 尝试转换为浮点数
                    float_value = float(profit_value)
                    data_b[item_id] = float_value
                except (ValueError, TypeError):
                    # 如果转换失败，记录警告并跳过
                    print(f"警告：报表B中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                    continue
        
        # 找出不同的数据
        differences = []
        all_items = set(data_a.keys()) | set(data_b.keys())
        
        for item in all_items:
            value_a = data_a.get(item, 0)
            value_b = data_b.get(item, 0)
            
            if abs(value_a - value_b) > 0.01:  # 允许0.01的误差
                differences.append({
                    'item': item,
                    'value_a': f"{value_a:.2f}",
                    'value_b': f"{value_b:.2f}",
                    'difference': round(value_b - value_a, 2)
                })
        
        # 为两个报表添加对比列
        # 为报表A添加对比列
        df_a['数据一致性'] = '否'  # 默认设为否
        for idx, row in df_a.iterrows():
            item_id = str(row[id_column_a]).strip()
            value_a = data_a.get(item_id, 0)
            value_b = data_b.get(item_id, 0)
            if abs(value_a - value_b) <= 0.01:  # 如果差异小于等于0.01，认为相同
                df_a.at[idx, '数据一致性'] = '是'
        
        # 为报表B添加对比列
        df_b['数据一致性'] = '否'  # 默认设为否
        for idx, row in df_b.iterrows():
            item_id = str(row[id_column_b]).strip()
            value_a = data_a.get(item_id, 0)
            value_b = data_b.get(item_id, 0)
            if abs(value_a - value_b) <= 0.01:  # 如果差异小于等于0.01，认为相同
                df_b.at[idx, '数据一致性'] = '是'
        
        # 保存带有对比结果的报表到临时目录
        temp_dir = tempfile.mkdtemp()
        report_a_filename = f'报表A_对比结果_{os.path.basename(report_a.filename)}'
        report_b_filename = f'报表B_对比结果_{os.path.basename(report_b.filename)}'
        report_a_path = os.path.join(temp_dir, report_a_filename)
        report_b_path = os.path.join(temp_dir, report_b_filename)
        
        # 根据原文件格式保存
        if report_a.filename.lower().endswith('.csv'):
            df_a.to_csv(report_a_path, index=False, encoding='utf-8-sig')
        else:
            # 保存为Excel文件
            try:
                df_a.to_excel(report_a_path, index=False, engine='openpyxl')
            except:
                try:
                    df_a.to_excel(report_a_path, index=False, engine='xlwt')
                except:
                    # 最后尝试不指定引擎
                    df_a.to_excel(report_a_path, index=False)
            
        if report_b.filename.lower().endswith('.csv'):
            df_b.to_csv(report_b_path, index=False, encoding='utf-8-sig')
        else:
            # 保存为Excel文件
            try:
                df_b.to_excel(report_b_path, index=False, engine='openpyxl')
            except:
                try:
                    df_b.to_excel(report_b_path, index=False, engine='xlwt')
                except:
                    # 最后尝试不指定引擎
                    df_b.to_excel(report_b_path, index=False)
        
        # 将文件路径存储到session中供下载使用
        from flask import session
        session['report_a_path'] = report_a_path
        session['report_b_path'] = report_b_path
        session['report_a_filename'] = report_a_filename
        session['report_b_filename'] = report_b_filename
        
        # 统计信息
        summary = {
            'total_a': len(data_a),
            'total_b': len(data_b),
            'matched': len(all_items) - len(differences),
            'differences': len(differences)
        }
        
        # 添加处理信息
        processed_info = {
            'total_rows_a': len(df_a),
            'total_rows_b': len(df_b),
            'valid_profit_a': len(data_a),
            'valid_profit_b': len(data_b),
            'skipped_a': len(df_a) - len(data_a),
            'skipped_b': len(df_b) - len(data_b)
        }
        
        return jsonify({
            'success': True,
            'differences': differences,
            'summary': summary,
            'processed_info': processed_info
        })
        
    except Exception as e:
        print(f"Debug: 最终错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@athina_blue.route('/athina_performance_settlement')
@login_required
@staff_only
def athina_performance_settlement():
    """员工业绩结算页面
    显示符合结算标准的记录：is_all_invoiced=True（不再要求余额为0）
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        
        # 筛选参数
        filter_consultant = request.args.get('filter_consultant', '')
        filter_sales_consultant = request.args.get('filter_sales_consultant', '')
        filter_book_date_from = request.args.get('filter_book_date_from', '')
        filter_book_date_to = request.args.get('filter_book_date_to', '')
        filter_is_count_performance = request.args.get('filter_is_count_performance', '')
        filter_balance = request.args.get('filter_balance', '')  # 'zero_or_negative': 小于等于0, 'positive': 大于0
        
        # 构建查询
        # 结算标准：is_all_invoiced=True 且 sub_total_balance=0（或为NULL但实际应为0）
        # 如果有搜索条件或筛选条件，显示匹配的记录（包括不符合结算条件的）
        # 如果没有任何筛选条件，只显示符合结算标准的记录
        
        has_filters = (filter_consultant or filter_sales_consultant or 
                      filter_book_date_from or filter_book_date_to or 
                      filter_is_count_performance != '' or filter_balance != '')
        
        if search and search.strip():
            # 有搜索时，搜索所有记录，不限制结算条件
            query = AthinaBookingHeader.query.filter(
                db.or_(
                    AthinaBookingHeader.booking_header_id.contains(search),
                    AthinaBookingHeader.corporate_name.contains(search)
                )
            )
        elif has_filters:
            # 有筛选条件时，显示所有记录（让筛选条件来过滤）
            query = AthinaBookingHeader.query
        else:
            # 无搜索无筛选时，只显示符合结算标准的记录（只需 is_all_invoiced = True）
            query = AthinaBookingHeader.query.filter(
                AthinaBookingHeader.is_all_invoiced == True
            )
        
        # 应用筛选条件（确保字段不为NULL时才使用contains）
        if filter_consultant:
            query = query.filter(
                AthinaBookingHeader.consultant.isnot(None),
                AthinaBookingHeader.consultant != '',
                AthinaBookingHeader.consultant.contains(filter_consultant)
            )
        
        if filter_sales_consultant:
            query = query.filter(
                AthinaBookingHeader.sales_consultant.isnot(None),
                AthinaBookingHeader.sales_consultant != '',
                AthinaBookingHeader.sales_consultant.contains(filter_sales_consultant)
            )
        
        if filter_book_date_from:
            query = query.filter(AthinaBookingHeader.book_date >= filter_book_date_from)
        
        if filter_book_date_to:
            query = query.filter(AthinaBookingHeader.book_date <= filter_book_date_to)
        
        if filter_is_count_performance != '':
            is_count_perf = filter_is_count_performance.lower() == 'true'
            query = query.filter(AthinaBookingHeader.is_count_performance == is_count_perf)
        
        # 余额筛选
        if filter_balance != '':
            if filter_balance == 'zero_or_negative':
                # 筛选余额小于等于0的记录（包括NULL）
                # 使用 COALESCE 将 NULL 视为 0，这样可以直接比较
                from sqlalchemy import func
                query = query.filter(
                    func.coalesce(AthinaBookingHeader.sub_total_balance, 0) <= 0
                )
            elif filter_balance == 'positive':
                # 筛选余额大于0的记录（排除NULL）
                query = query.filter(
                    AthinaBookingHeader.sub_total_balance.isnot(None),
                    AthinaBookingHeader.sub_total_balance > 0
                )
        
        # 保存用于汇总的查询（不带排序）
        summary_query_base = query
        
        # 计算筛选结果的总和统计（基于相同的筛选条件，但不分页和排序）
        from sqlalchemy import func
        summary_total_pl = summary_query_base.with_entities(
            func.sum(AthinaBookingHeader.sub_total_pl)
        ).scalar() or 0
        
        summary_operator_profit = summary_query_base.with_entities(
            func.sum(AthinaBookingHeader.operator_profit)
        ).scalar() or 0
        
        summary_sales_profit = summary_query_base.with_entities(
            func.sum(AthinaBookingHeader.sales_profit)
        ).scalar() or 0
        
        summary_company_profit = summary_query_base.with_entities(
            func.sum(AthinaBookingHeader.company_profit)
        ).scalar() or 0
        
        # 按HID从小到大排序（最小的HID显示在最前面）
        # 先尝试转换为数字排序，如果失败则按字符串排序
        from sqlalchemy import func, case
        # 使用MySQL的CAST函数将字符串转换为无符号整数进行排序
        query = query.order_by(
            func.cast(AthinaBookingHeader.booking_header_id, db.Integer).asc()
        )
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # 更新所有header的开票状态
        headers_with_details = []
        for header in pagination.items:
            header.update_invoice_status()
            headers_with_details.append(header)
        
        db.session.commit()
        
        # 计算统计信息（只要求 is_all_invoiced = True）
        total_query = AthinaBookingHeader.query.filter(
            AthinaBookingHeader.is_all_invoiced == True
        )
        
        total_count = total_query.count()
        total_profit = db.session.query(db.func.sum(AthinaBookingHeader.sub_total_pl)).filter(
            AthinaBookingHeader.is_all_invoiced == True
        ).scalar() or 0
        
        settled_count = total_query.filter(AthinaBookingHeader.is_count_performance == True).count()
        unsettled_count = total_query.filter(AthinaBookingHeader.is_count_performance == False).count()
        
        # 获取唯一的顾问列表用于筛选（只要求 is_all_invoiced = True）
        consultants = db.session.query(AthinaBookingHeader.consultant).distinct().filter(
            AthinaBookingHeader.consultant.isnot(None),
            AthinaBookingHeader.consultant != '',
            AthinaBookingHeader.is_all_invoiced == True
        ).order_by(AthinaBookingHeader.consultant).all()
        consultants = [c[0] for c in consultants]
        
        sales_consultants = db.session.query(AthinaBookingHeader.sales_consultant).distinct().filter(
            AthinaBookingHeader.sales_consultant.isnot(None),
            AthinaBookingHeader.sales_consultant != '',
            AthinaBookingHeader.is_all_invoiced == True
        ).order_by(AthinaBookingHeader.sales_consultant).all()
        sales_consultants = [c[0] for c in sales_consultants]
        
        return render_template('finance/athina/athina_performance_settlement.html',
                             headers=headers_with_details,
                             pagination=pagination,
                             search=search,
                             filter_consultant=filter_consultant,
                             filter_sales_consultant=filter_sales_consultant,
                             filter_book_date_from=filter_book_date_from,
                             filter_book_date_to=filter_book_date_to,
                             filter_is_count_performance=filter_is_count_performance,
                             filter_balance=filter_balance,
                             consultants=consultants,
                             sales_consultants=sales_consultants,
                             total_count=total_count,
                             total_profit=float(total_profit),
                             settled_count=settled_count,
                             unsettled_count=unsettled_count,
                             summary_total_pl=float(summary_total_pl),
                             summary_operator_profit=float(summary_operator_profit),
                             summary_sales_profit=float(summary_sales_profit),
                             summary_company_profit=float(summary_company_profit))
        
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('athina_routes.athina_header_data'))


def build_performance_settlement_query(search, filter_consultant, filter_sales_consultant, 
                                       filter_book_date_from, filter_book_date_to,
                                       filter_is_count_performance, filter_balance):
    """构建业绩结算查询的辅助函数"""
    has_filters = (filter_consultant or filter_sales_consultant or 
                  filter_book_date_from or filter_book_date_to or 
                  filter_is_count_performance != '' or filter_balance != '')
    
    if search and search.strip():
        query = AthinaBookingHeader.query.filter(
            db.or_(
                AthinaBookingHeader.booking_header_id.contains(search),
                AthinaBookingHeader.corporate_name.contains(search)
            )
        )
    elif has_filters:
        query = AthinaBookingHeader.query
    else:
        query = AthinaBookingHeader.query.filter(
            AthinaBookingHeader.is_all_invoiced == True
        )
    
    if filter_consultant:
        query = query.filter(
            AthinaBookingHeader.consultant.isnot(None),
            AthinaBookingHeader.consultant != '',
            AthinaBookingHeader.consultant.contains(filter_consultant)
        )
    
    if filter_sales_consultant:
        query = query.filter(
            AthinaBookingHeader.sales_consultant.isnot(None),
            AthinaBookingHeader.sales_consultant != '',
            AthinaBookingHeader.sales_consultant.contains(filter_sales_consultant)
        )
    
    if filter_book_date_from:
        query = query.filter(AthinaBookingHeader.book_date >= filter_book_date_from)
    
    if filter_book_date_to:
        query = query.filter(AthinaBookingHeader.book_date <= filter_book_date_to)
    
    if filter_is_count_performance != '':
        is_count_perf = filter_is_count_performance.lower() == 'true'
        query = query.filter(AthinaBookingHeader.is_count_performance == is_count_perf)
    
    if filter_balance != '':
        from sqlalchemy import func
        if filter_balance == 'zero_or_negative':
            query = query.filter(
                func.coalesce(AthinaBookingHeader.sub_total_balance, 0) <= 0
            )
        elif filter_balance == 'positive':
            query = query.filter(
                AthinaBookingHeader.sub_total_balance.isnot(None),
                AthinaBookingHeader.sub_total_balance > 0
            )
    
    return query


@athina_blue.route('/athina_performance_settlement_export', methods=['GET'])
@login_required
@staff_only
def athina_performance_settlement_export():
    """导出业绩结算筛选结果为Excel"""
    try:
        # 获取筛选参数（与页面筛选相同）
        search = request.args.get('search', '')
        filter_consultant = request.args.get('filter_consultant', '')
        filter_sales_consultant = request.args.get('filter_sales_consultant', '')
        filter_book_date_from = request.args.get('filter_book_date_from', '')
        filter_book_date_to = request.args.get('filter_book_date_to', '')
        filter_is_count_performance = request.args.get('filter_is_count_performance', '')
        filter_balance = request.args.get('filter_balance', '')
        
        # 构建查询（使用辅助函数）
        query = build_performance_settlement_query(
            search, filter_consultant, filter_sales_consultant,
            filter_book_date_from, filter_book_date_to,
            filter_is_count_performance, filter_balance
        )
        
        # 按HID排序
        from sqlalchemy import func
        query = query.order_by(
            func.cast(AthinaBookingHeader.booking_header_id, db.Integer).asc()
        )
        
        # 获取所有数据（不分页）
        headers = query.all()
        
        # 准备Excel数据
        data = []
        for header in headers:
            data.append({
                'HID': header.booking_header_id,
                '公司名称': header.corporate_name or '',
                '预订日期': header.book_date.strftime('%Y-%m-%d') if header.book_date else '',
                '总金额': float(header.sub_total_gross) if header.sub_total_gross else 0.00,
                '成本': float(header.sub_total_cost) if header.sub_total_cost else 0.00,
                '盈亏': float(header.sub_total_pl) if header.sub_total_pl else 0.00,
                '余额': float(header.sub_total_balance) if header.sub_total_balance else 0.00,
                '操作员': header.consultant or '',
                '业务员': header.sales_consultant or '',
                '是否已开票': '是' if header.is_all_invoiced else '否',
                '是否已核算业绩': '是' if header.is_count_performance else '否',
                '订单类型': header.order_type or '',
                '操作员利润': float(header.operator_profit) if header.operator_profit else 0.00,
                '业务员利润': float(header.sales_profit) if header.sales_profit else 0.00,
                '公司利润': float(header.company_profit) if header.company_profit else 0.00,
            })
        
        if not data:
            flash('没有数据可导出', 'warning')
            return redirect(url_for('athina_routes.athina_performance_settlement'))
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='业绩结算数据')
            worksheet = writer.sheets['业绩结算数据']
            
            # 设置列宽
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max() if len(df) > 0 else 0,
                    len(col)
                ) + 2
                col_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        
        output.seek(0)
        filename = f'业绩结算数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f'导出Excel失败: {str(e)}', exc_info=True)
        flash(f'导出失败: {str(e)}', 'error')
        return redirect(url_for('athina_routes.athina_performance_settlement'))


@athina_blue.route('/athina_batch_settle_performance', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_batch_settle_performance():
    """批量标记为已核算业绩"""
    try:
        data = request.get_json()
        header_ids = data.get('header_ids', [])
        
        if not header_ids:
            return jsonify({
                'success': False,
                'message': '请选择要结算的记录'
            }), 400
        
        # 验证所有记录都符合结算标准（只要求 is_all_invoiced = True）
        headers = AthinaBookingHeader.query.filter(
            AthinaBookingHeader.id.in_(header_ids),
            AthinaBookingHeader.is_all_invoiced == True
        ).all()
        
        if len(headers) != len(header_ids):
            return jsonify({
                'success': False,
                'message': '部分记录不符合结算标准（必须已开票）'
            }), 400
        
        # 批量标记为已核算业绩
        count = 0
        for header in headers:
            if not header.is_count_performance:
                header.is_count_performance = True
                count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功标记 {count} 条记录为已核算业绩',
            'count': count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'批量结算失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_calculate_profit_distribution', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_calculate_profit_distribution():
    """计算并更新利润分配"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution, get_order_type
        from decimal import Decimal
        
        data = request.get_json()
        header_ids = data.get('header_ids', [])
        
        if not header_ids:
            return jsonify({
                'success': False,
                'message': '请选择要计算利润分配的记录'
            }), 400
        
        # 获取所有选中的记录
        headers = AthinaBookingHeader.query.filter(
            AthinaBookingHeader.id.in_(header_ids)
        ).all()
        
        if len(headers) != len(header_ids):
            return jsonify({
                'success': False,
                'message': '部分记录不存在'
            }), 400
        
        # 计算并更新利润分配
        success_count = 0
        error_count = 0
        errors = []
        
        for header in headers:
            try:
                # 获取订单金额和利润，确保转换为Decimal类型
                order_amount = header.sub_total_gross
                if order_amount is None:
                    order_amount = Decimal('0')
                elif not isinstance(order_amount, Decimal):
                    order_amount = Decimal(str(order_amount))
                
                profit = header.sub_total_pl
                if profit is None:
                    profit = Decimal('0')
                elif not isinstance(profit, Decimal):
                    profit = Decimal(str(profit))
                
                # 获取订单类型（根据盈亏金额判断，无论利润是否为0都需要设置）
                order_type = get_order_type(profit)
                
                # 如果利润为0，不分配
                if profit == 0:
                    header.operator_profit = Decimal('0')
                    header.sales_profit = Decimal('0')
                    header.company_profit = Decimal('0')
                    header.order_type = order_type
                else:
                    # 计算利润分配（基于盈亏金额，包括负数亏损）
                    operator_profit, sales_profit, company_profit = calculate_profit_distribution(
                        profit
                    )
                    
                    # 更新到数据库
                    header.operator_profit = operator_profit
                    header.sales_profit = sales_profit
                    header.company_profit = company_profit
                    header.order_type = order_type
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f'HID {header.booking_header_id}: {str(e)}')
                logger.error(f'计算利润分配失败 (HID: {header.booking_header_id}): {str(e)}')
        
        # 提交所有更改
        db.session.commit()
        
        message = f'成功计算 {success_count} 条记录的利润分配'
        if error_count > 0:
            message += f'，{error_count} 条记录失败'
        
        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量计算利润分配失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'批量计算失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_calculate_all_unsettled_profit_distribution', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_calculate_all_unsettled_profit_distribution():
    """计算全部未结算单的利润分配"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution, get_order_type
        from decimal import Decimal
        
        # 查询所有未结算单（is_count_performance = False）
        headers = AthinaBookingHeader.query.filter(
            AthinaBookingHeader.is_count_performance == False
        ).all()
        
        if not headers:
            return jsonify({
                'success': True,
                'message': '没有找到未结算单',
                'success_count': 0,
                'error_count': 0
            })
        
        # 计算并更新利润分配
        success_count = 0
        error_count = 0
        errors = []
        
        for header in headers:
            try:
                # 获取订单金额和利润，确保转换为Decimal类型
                order_amount = header.sub_total_gross
                if order_amount is None:
                    order_amount = Decimal('0')
                elif not isinstance(order_amount, Decimal):
                    order_amount = Decimal(str(order_amount))
                
                profit = header.sub_total_pl
                if profit is None:
                    profit = Decimal('0')
                elif not isinstance(profit, Decimal):
                    profit = Decimal(str(profit))
                
                # 获取订单类型（根据盈亏金额判断，无论利润是否为0都需要设置）
                order_type = get_order_type(profit)
                
                # 如果利润为0，不分配
                if profit == 0:
                    header.operator_profit = Decimal('0')
                    header.sales_profit = Decimal('0')
                    header.company_profit = Decimal('0')
                    header.order_type = order_type
                else:
                    # 计算利润分配（基于盈亏金额，包括负数亏损）
                    operator_profit, sales_profit, company_profit = calculate_profit_distribution(
                        profit
                    )
                    
                    # 更新到数据库
                    header.operator_profit = operator_profit
                    header.sales_profit = sales_profit
                    header.company_profit = company_profit
                    header.order_type = order_type
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f'HID {header.booking_header_id}: {str(e)}')
                logger.error(f'计算利润分配失败 (HID: {header.booking_header_id}): {str(e)}')
        
        # 提交所有更改
        db.session.commit()
        
        message = f'成功计算 {success_count} 条未结算单的利润分配'
        if error_count > 0:
            message += f'，{error_count} 条记录失败'
        
        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量计算全部未结算单利润分配失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'批量计算失败: {str(e)}'
        }), 500


@athina_blue.route('/download_report/<report_type>', methods=['GET'])
@csrf.exempt
def download_report(report_type):
    """下载带有对比结果的报表文件"""
    try:
        from flask import session, send_file
        
        if report_type == 'A':
            file_path = session.get('report_a_path')
            filename = session.get('report_a_filename', '报表A_对比结果.xlsx')
        elif report_type == 'B':
            file_path = session.get('report_b_path')
            filename = session.get('report_b_filename', '报表B_对比结果.xlsx')
        else:
            return jsonify({'success': False, 'error': '无效的报表类型'})
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在，请重新进行对比'})
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@athina_blue.route('/batch_compare_reports', methods=['POST'])
@csrf.exempt
def batch_compare_reports():
    """批量对比两个文件夹中的报表"""
    try:
        print("=== 开始处理批量报表对比请求 ===")
        
        # 获取上传的文件
        folder_a_files = request.files.getlist('folder_a_files')
        folder_b_files = request.files.getlist('folder_b_files')
        
        print(f"Debug: 文件夹A文件数量 = {len(folder_a_files)}")
        print(f"Debug: 文件夹B文件数量 = {len(folder_b_files)}")
        
        if not folder_a_files:
            return jsonify({'success': False, 'error': '请选择文件夹A的文件'})
        
        if not folder_b_files:
            return jsonify({'success': False, 'error': '请选择文件夹B的文件'})
        
        # 过滤出Excel和CSV文件
        def filter_report_files(files):
            return [f for f in files if f.filename.lower().endswith(('.xlsx', '.xls', '.csv'))]
        
        folder_a_files = filter_report_files(folder_a_files)
        folder_b_files = filter_report_files(folder_b_files)
        
        print(f"Debug: 过滤后文件夹A文件数量 = {len(folder_a_files)}")
        print(f"Debug: 过滤后文件夹B文件数量 = {len(folder_b_files)}")
        
        if not folder_a_files:
            return jsonify({'success': False, 'error': '文件夹A中没有有效的报表文件'})
        
        if not folder_b_files:
            return jsonify({'success': False, 'error': '文件夹B中没有有效的报表文件'})
        
        return jsonify({
            'success': False,
            'error': '批量报表对比功能暂时不可用，正在开发中...'
        })
        
    except Exception as e:
        print(f"Debug: 批量对比最终错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@athina_blue.route('/download_batch_report', methods=['GET'])
@csrf.exempt
def download_batch_report():
    """下载批量对比汇总报告"""
    try:
        from flask import session, send_file
        
        file_path = session.get('batch_report_path')
        filename = session.get('batch_report_filename', '批量报表对比报告.xlsx')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '报告文件不存在，请重新进行批量对比'})
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@athina_blue.route('/open_booking_folder', methods=['GET'])
@login_required
@staff_only
def open_booking_folder():
    """打开账单文件夹"""
    try:
        import subprocess
        from App_new.config import Config
        from pathlib import Path
        
        # 获取账单文件夹路径
        booking_folder = Path(Config.BILLING_DATA_PATH) / "BOOKING" / "Zz"
        
        if not booking_folder.exists():
            return jsonify({
                'error': f'文件夹不存在: {booking_folder}',
                'success': False
            }), 404
        
        # 在Windows中打开文件夹
        subprocess.Popen(f'explorer "{booking_folder}"')
        
        return jsonify({
            'success': True,
            'message': '文件夹已打开'
        })
        
    except Exception as e:
        error_msg = f'打开文件夹失败: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': error_msg, 'success': False}), 500


@athina_blue.route('/athina_export_unsettled', methods=['GET'])
@login_required
@staff_only
def export_unsettled_orders():
    """导出未结算订单到Excel"""
    try:
        logger.info('开始导出未结算订单')
        
        from App_new.utils.Invoice import CountHid
        from App_new.config import Config
        from pathlib import Path
        
        # 初始化CountHid类
        booking_path = Path(Config.BILLING_DATA_PATH) / 'BOOKING'
        
        if not booking_path.exists():
            error_msg = f'账单路径不存在: {booking_path}'
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'success': False}), 404
        
        # 创建CountHid实例
        count_hid = CountHid(str(booking_path), name='Zz')
        
        # 导出未结算订单
        success = count_hid.export_unsettled_orders()
        
        if success:
            message = f'✅ 未结算订单已成功导出到: {booking_path / "Zz"} 文件夹'
            logger.info(message)
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            error_msg = '导出失败：没有未结算订单或发生错误'
            logger.warning(error_msg)
            return jsonify({
                'error': error_msg,
                'success': False
            }), 400
            
    except Exception as e:
        error_msg = f'导出未结算订单时出错: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': error_msg, 'success': False}), 500


# ==================== Athina 数据导入到项目系统 ====================

@athina_blue.route('/athina_to_project')
@login_required
@staff_only
def athina_to_project():
    """Athina 数据导入到项目系统页面"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    service = AthinaToProjectService(
        current_user_id=current_user.id,
        current_user_name=current_user.username
    )

    # 获取筛选参数
    search = request.args.get('search', '')
    filter_imported = request.args.get('filter_imported', '')  # 'imported', 'not_imported', ''
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 使用优化后的分页查询
    result = service.get_importable_athina_headers_paginated(search, filter_imported, page, per_page)
    items = result['items']

    # 构造分页对象
    class SimplePagination:
        def __init__(self, page, per_page, total, pages, has_prev, has_next):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = pages
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = page - 1
            self.next_num = page + 1

        def iter_pages(self):
            # 智能分页：显示首页、末页、当前页附近的页码
            if self.pages <= 7:
                for i in range(1, self.pages + 1):
                    yield i
            else:
                # 显示：1 ... 当前-1 当前 当前+1 ... 末页
                yield 1
                if self.page > 3:
                    yield None  # 省略号
                for i in range(max(2, self.page - 1), min(self.pages, self.page + 2)):
                    yield i
                if self.page < self.pages - 2:
                    yield None  # 省略号
                if self.pages > 1:
                    yield self.pages

    pagination = SimplePagination(
        result['page'], result['per_page'], result['total'],
        result['pages'], result['has_prev'], result['has_next']
    )

    # 统计信息 - 在 Python 层面计算，避免 collation 冲突
    from App_new.finance.models.athina_booking import AthinaBookingHeader
    from App_new.business.projects.models.project import ProjectHeader

    # 获取所有 Athina HID
    athina_hids = {h[0] for h in db.session.query(AthinaBookingHeader.booking_header_id).all()}
    # 获取所有已导入的 HID
    imported_hids = {h[0] for h in db.session.query(ProjectHeader.hid).all()}
    # 计算交集
    imported_count = len(athina_hids & imported_hids)

    stats = {
        'total': len(athina_hids),
        'imported': imported_count,
        'not_imported': len(athina_hids) - imported_count,
    }

    return render_template('finance/athina/athina_to_project.html',
                           items=items,
                           pagination=pagination,
                           search=search,
                           filter_imported=filter_imported,
                           stats=stats)


@athina_blue.route('/athina_to_project/import/<int:header_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_to_project_import(header_id):
    """导入单个 Athina Header 到项目系统"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        data = request.get_json() or {}
        options = {
            'create_eo': data.get('create_eo', False),
            'create_invoice': data.get('create_invoice', False),
        }

        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.import_header_and_refs(header_id, options)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f'导入失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/batch_import', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_to_project_batch_import():
    """批量导入 Athina Headers 到项目系统"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        data = request.get_json() or {}
        header_ids = data.get('header_ids', [])
        options = {
            'create_eo': data.get('create_eo', False),
            'create_invoice': data.get('create_invoice', False),
        }

        if not header_ids:
            return jsonify({'success': False, 'message': '请选择要导入的记录'}), 400

        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.batch_import(header_ids, options)

        return jsonify(result)

    except Exception as e:
        logger.error(f'批量导入失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'批量导入失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/generate_eos/<int:project_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_to_project_generate_eos(project_id):
    """为项目生成 EO"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.generate_eos_for_project(project_id)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f'生成 EO 失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'生成 EO 失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/generate_receipt/<int:project_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_to_project_generate_receipt(project_id):
    """根据余额生成收款记录"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.generate_receipt_from_balance(project_id)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f'生成收款记录失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'生成收款记录失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/preview/<int:header_id>')
@login_required
@staff_only
def athina_to_project_preview(header_id):
    """预览 Athina Header 导入数据"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        athina_header = AthinaBookingHeader.query.get_or_404(header_id)
        details = athina_header.details.filter_by(is_subtotal=False).all()

        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )

        preview_data = {
            'header': {
                'hid': athina_header.booking_header_id,
                'corporate_name': athina_header.corporate_name,
                'book_date': athina_header.book_date.isoformat() if athina_header.book_date else None,
                'consultant': athina_header.consultant,
                'total_gross': float(athina_header.sub_total_gross) if athina_header.sub_total_gross else 0,
                'total_cost': float(athina_header.sub_total_cost) if athina_header.sub_total_cost else 0,
                'total_pl': float(athina_header.sub_total_pl) if athina_header.sub_total_pl else 0,
                'balance': float(athina_header.sub_total_balance) if athina_header.sub_total_balance else 0,
                'is_all_invoiced': athina_header.is_all_invoiced,
            },
            'details': [],
            'company_match': None,
            'warnings': [],
        }

        # 检查公司匹配
        from App_new.shared.models.customer_company import CustomerCompany
        if athina_header.corporate_name:
            company = CustomerCompany.query.filter(
                CustomerCompany.company_name.ilike(f'%{athina_header.corporate_name}%')
            ).first()
            if company:
                preview_data['company_match'] = {
                    'id': company.id,
                    'name': company.company_name,
                }
            else:
                preview_data['warnings'].append(f'未找到匹配的公司: {athina_header.corporate_name}')

        # 处理明细
        for detail in details:
            ref_type_id = service._get_business_type_id(detail.book_type)
            from App_new.shared.models.business_types import BusinessType
            ref_type = BusinessType.query.get(ref_type_id) if ref_type_id else None

            supplier_id = service._find_supplier(detail.supplier)
            supplier = CustomerCompany.query.get(supplier_id) if supplier_id else None

            preview_data['details'].append({
                'booking_ref': detail.booking_ref,
                'ref_number': f'R{detail.booking_ref}',
                'book_type': detail.book_type,
                'ref_type': ref_type.name if ref_type else '其他',
                'client_name': detail.client_name,
                'itin_desc': detail.itin_desc,
                'dep_date': detail.dep_date.isoformat() if detail.dep_date else None,
                'gross_amount': float(detail.gross_amount) if detail.gross_amount else 0,
                'local_cost': float(detail.local_cost) if detail.local_cost else 0,
                'profit': float(detail.profit_loss) if detail.profit_loss else 0,
                'supplier': detail.supplier,
                'supplier_match': supplier.company_name if supplier else None,
                'invoice_no': detail.invoice_no,
            })

            if detail.supplier and not supplier:
                preview_data['warnings'].append(f'未找到匹配的供应商: {detail.supplier}')

        return jsonify({'success': True, 'data': preview_data})

    except Exception as e:
        logger.error(f'预览失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'预览失败: {str(e)}'}), 500


# ==================== Athina CSV 文件导入到项目系统 ====================

@athina_blue.route('/athina_to_project/csv_import')
@login_required
@staff_only
def athina_to_project_csv_import():
    """Athina CSV 文件导入页面"""
    return render_template('finance/athina/athina_csv_import.html')


@athina_blue.route('/athina_to_project/import_reservation_csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_reservation_csv():
    """导入 Reservation Listing Report.csv (HID + REF)"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService
    import traceback

    try:
        logger.info('=== 开始导入 Reservation CSV ===')

        if 'file' not in request.files:
            logger.warning('未找到上传文件')
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.warning('文件名为空')
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        if not file.filename.lower().endswith('.csv'):
            logger.warning(f'文件格式错误: {file.filename}')
            return jsonify({'success': False, 'message': '请选择 CSV 格式文件'}), 400

        # 读取文件内容
        file_content = file.read()
        logger.info(f'文件大小: {len(file_content)} 字节, 文件名: {file.filename}')

        # 获取导入选项
        options = {
            'create_eo': request.form.get('create_eo', 'false').lower() == 'true',
            'create_invoice': request.form.get('create_invoice', 'false').lower() == 'true',
        }
        logger.info(f'导入选项: {options}')

        # 导入 - 传递当前用户信息，确保导入的项目能被用户看到
        logger.info(f'创建 AthinaToProjectService, user_id={current_user.id}')
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )

        logger.info('开始执行 import_reservation_csv...')
        result = service.import_reservation_csv(file_content, options)
        logger.info(f'导入完成: {result.get("message", "无消息")}')

        return jsonify(result)

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f'导入 Reservation CSV 失败: {str(e)}\n{error_trace}')
        print(f'[ERROR] 导入 Reservation CSV 失败: {str(e)}\n{error_trace}')
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/import_eo_csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_eo_csv():
    """导入 Exchange Order Listing Report.csv (EO)"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '请选择 CSV 格式文件'}), 400

        # 读取文件内容
        file_content = file.read()

        # 导入
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.import_eo_csv(file_content)

        return jsonify(result)

    except Exception as e:
        logger.error(f'导入 EO CSV 失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/import_invoice_csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_invoice_csv():
    """导入 Invoice Listing Report.csv (Invoice)"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '请选择 CSV 格式文件'}), 400

        # 读取文件内容
        file_content = file.read()

        # 导入
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.import_invoice_csv(file_content)

        return jsonify(result)

    except Exception as e:
        logger.error(f'导入 Invoice CSV 失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@athina_blue.route('/athina_to_project/import_receipt_csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_receipt_csv():
    """导入 Receipt.csv (收款记录)"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '请选择 CSV 格式文件'}), 400

        # 读取文件内容
        file_content = file.read()

        # 导入
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.import_receipt_csv(file_content)

        return jsonify(result)

    except Exception as e:
        logger.error(f'导入 Receipt CSV 失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@athina_blue.route('/import/payment-voucher-csv', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_import_payment_voucher_csv():
    """导入 Payment Voucher CSV (付款凭证)"""
    from App_new.finance.services.athina_to_project_service import AthinaToProjectService

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '请选择 CSV 格式文件'}), 400

        # 读取文件内容
        file_content = file.read()

        # 导入
        service = AthinaToProjectService(
            current_user_id=current_user.id,
            current_user_name=current_user.username
        )
        result = service.import_payment_voucher_csv(file_content)

        return jsonify(result)

    except Exception as e:
        logger.error(f'导入 Payment Voucher CSV 失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
