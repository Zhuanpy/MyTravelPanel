# -*- coding: utf-8 -*-
"""Athina 相关路由"""

from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, send_file
from io import BytesIO
from flask_login import login_required, current_user
from App_new.exts import csrf, db
from App_new.utils.decorators import staff_only
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


## Athina 页面和CSV导入路由已删除（数据已迁移到 ProjectHeader）


@athina_blue.route('/athina_stats')
@login_required
@staff_only
def athina_stats():
    """Athina数据统计（已废弃）"""
    return jsonify({'success': False, 'message': 'Athina数据已迁移到项目系统'}), 410


@athina_blue.route('/athina_header_data')
@login_required
@staff_only
def athina_header_data():
    """Athina数据查看（已废弃，重定向到业绩结算页面）"""
    return redirect(url_for('athina_routes.athina_performance_settlement'))


# ---- 以下为已删除的 Athina 数据管理路由的占位符 ----
# athina_clear_data, athina_recalculate_subtotals, athina_toggle_performance,
# athina_update_consultants, athina_delete_header, athina_detail
# 这些路由操作的是已删除的 athina_booking_headers/details 表，不再需要


_ATHINA_REMOVED_MSG = """以下Athina旧数据路由已删除（数据已迁移到ProjectHeader）:
athina_stats, athina_header_data(仅保留重定向), athina_clear_data,
athina_recalculate_subtotals, athina_toggle_performance, athina_update_consultants,
athina_delete_header, athina_detail"""  # noqa: E501 - 仅文档用


# ---- 保留的路由从这里开始 ----
# 以下是不依赖 AthinaBookingHeader/Detail 的路由


## 以下 Athina 旧数据管理路由已删除（athina_booking_headers/details 表已废弃）:
# athina_clear_data, athina_recalculate_subtotals, athina_toggle_performance,
# athina_update_consultants, athina_delete_header, athina_detail


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
            return redirect(url_for("athina_routes.athina_performance_settlement"))
    
    try:
        os.startfile(str(folder_path))
        flash('成功打开BOOKING文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect(url_for("athina_routes.athina_performance_settlement"))


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


def _get_staff_list():
    """获取员工列表（staff和admin角色），返回 [{'id': ..., 'name': ...}]"""
    from App_new.auth.models.auth import AuthUser, Role, UserProfile
    staff_role = Role.query.filter_by(name='staff').first()
    admin_role = Role.query.filter_by(name='admin').first()
    role_ids = []
    if staff_role:
        role_ids.append(staff_role.id)
    if admin_role:
        role_ids.append(admin_role.id)
    if not role_ids:
        return []
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
    result = []
    for u in staff_users:
        if u.first_name or u.last_name:
            display_name = f"{u.first_name or ''}{u.last_name or ''}".strip()
        else:
            display_name = u.username
        result.append({'id': u.id, 'name': display_name})
    return result


def _build_staff_name_map(staff_list):
    """从 staff_list 构建 {id: name} 映射"""
    return {s['id']: s['name'] for s in staff_list}


def _resolve_project_staff_display(projects, staff_name_map):
    """根据 operator_ids/salesperson_ids 解析每个项目的操作员/业务员显示名称"""
    result = {}
    for p in projects:
        op_ids = [int(s.strip()) for s in (p.operator_ids or '').split(',') if s.strip() and s.strip().isdigit()]
        sp_ids = [int(s.strip()) for s in (p.salesperson_ids or '').split(',') if s.strip() and s.strip().isdigit()]
        result[p.id] = {
            'operator_names': ', '.join(staff_name_map.get(uid, f'ID:{uid}') for uid in op_ids) if op_ids else (p.operator_names or '-'),
            'salesperson_names': ', '.join(staff_name_map.get(uid, f'ID:{uid}') for uid in sp_ids) if sp_ids else (p.salesperson_names or '-'),
        }
    return result


def _get_can_settle_project_ids():
    """获取所有可结算项目的 ID 集合（ref>0, ref==eo, eo==paid, ref==invoiced, balance==0）

    收款计算方式与项目列表一致，使用发票分配表正确处理跨项目收款：
    - 方式1: 项目级别收款通过发票分配表统计
    - 方式2: REF级别直接收款
    """
    from sqlalchemy import func, union_all
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
    from App_new.business.projects.models.eo import ProjectEO
    from App_new.business.projects.models.invoice import InvoiceItem, ProjectInvoice

    ref_count_subq = db.session.query(
        ProjectRef.header_id,
        func.count(ProjectRef.id).label('ref_count')
    ).group_by(ProjectRef.header_id).subquery()

    invoiced_ref_subq = db.session.query(
        ProjectRef.header_id,
        func.count(db.distinct(InvoiceItem.ref_id)).label('inv_ref_count')
    ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id
    ).group_by(ProjectRef.header_id).subquery()

    eo_count_subq = db.session.query(
        ProjectRef.header_id,
        func.count(ProjectEO.id).label('eo_count')
    ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
    ).group_by(ProjectRef.header_id).subquery()

    paid_eo_subq = db.session.query(
        ProjectRef.header_id,
        func.count(ProjectEO.id).label('paid_count')
    ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
    ).filter(ProjectEO.is_paid == True
    ).group_by(ProjectRef.header_id).subquery()

    sell_subq = db.session.query(
        ProjectRef.header_id,
        func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_sell')
    ).group_by(ProjectRef.header_id).subquery()

    # 收款计算：与项目列表保持一致，使用发票分配表
    # 方式1: 项目级别收款通过发票分配表统计（正确处理跨项目收款）
    invoice_alloc_q = db.session.query(
        ProjectInvoice.header_id.label('header_id'),
        ReceiptInvoiceAllocation.allocated_amount.label('amount')
    ).join(
        ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
    ).join(
        ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
    ).filter(
        ProjectReceipt.status == 'confirmed',
        ProjectReceipt.ref_id == None  # 仅项目级别收款
    )

    # 方式2: REF级别直接收款
    ref_receipt_q = db.session.query(
        ProjectReceipt.header_id.label('header_id'),
        ProjectReceipt.amount.label('amount')
    ).filter(
        ProjectReceipt.status == 'confirmed',
        ProjectReceipt.ref_id.isnot(None)
    )

    combined = union_all(invoice_alloc_q, ref_receipt_q).alias('combined_receipts')
    rcpt_subq = db.session.query(
        combined.c.header_id,
        func.coalesce(func.sum(combined.c.amount), 0).label('total_rcpt')
    ).group_by(combined.c.header_id).subquery()

    rows = db.session.query(ref_count_subq.c.header_id).outerjoin(
        eo_count_subq, ref_count_subq.c.header_id == eo_count_subq.c.header_id
    ).outerjoin(
        paid_eo_subq, ref_count_subq.c.header_id == paid_eo_subq.c.header_id
    ).outerjoin(
        invoiced_ref_subq, ref_count_subq.c.header_id == invoiced_ref_subq.c.header_id
    ).outerjoin(
        sell_subq, ref_count_subq.c.header_id == sell_subq.c.header_id
    ).outerjoin(
        rcpt_subq, ref_count_subq.c.header_id == rcpt_subq.c.header_id
    ).filter(
        ref_count_subq.c.ref_count > 0,
        ref_count_subq.c.ref_count == func.coalesce(eo_count_subq.c.eo_count, 0),
        func.coalesce(eo_count_subq.c.eo_count, 0) == func.coalesce(paid_eo_subq.c.paid_count, 0),
        ref_count_subq.c.ref_count == func.coalesce(invoiced_ref_subq.c.inv_ref_count, 0),
        func.abs(func.coalesce(sell_subq.c.total_sell, 0) - func.coalesce(rcpt_subq.c.total_rcpt, 0)) < 0.01
    ).all()

    return {r[0] for r in rows}


@athina_blue.route('/athina_performance_settlement')
@login_required
@staff_only
def athina_performance_settlement():
    """员工业绩结算页面（基于ProjectHeader）"""
    try:
        from sqlalchemy import func
        from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.invoice import ProjectInvoice

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')

        # 筛选参数
        filter_consultant = request.args.get('filter_consultant', '')
        filter_sales_consultant = request.args.get('filter_sales_consultant', '')
        filter_book_date_from = request.args.get('filter_book_date_from', '')
        filter_book_date_to = request.args.get('filter_book_date_to', '')
        filter_is_count_performance = request.args.get('filter_is_count_performance', '')
        filter_balance = request.args.get('filter_balance', '')
        filter_can_settle = request.args.get('filter_can_settle', '')
        filter_order_type = request.args.get('filter_order_type', '')

        # 使用辅助函数构建查询
        query = build_performance_settlement_query(
            search, filter_consultant, filter_sales_consultant,
            filter_book_date_from, filter_book_date_to,
            filter_is_count_performance, filter_balance,
            filter_can_settle, filter_order_type
        )

        # 汇总统计（基于筛选条件，不分页）
        filtered_ids_query = query.with_entities(ProjectHeader.id)

        # 利润分配汇总
        summary_operator_profit = query.with_entities(
            func.sum(ProjectHeader.operator_profit)
        ).scalar() or 0
        summary_sales_profit = query.with_entities(
            func.sum(ProjectHeader.sales_profit)
        ).scalar() or 0
        summary_company_profit = query.with_entities(
            func.sum(ProjectHeader.company_profit)
        ).scalar() or 0

        # 从REF聚合金额、成本、盈亏
        ref_summary = db.session.query(
            func.coalesce(func.sum(ProjectRef.selling_price), 0),
            func.coalesce(func.sum(ProjectRef.cost_price), 0)
        ).filter(
            ProjectRef.header_id.in_(filtered_ids_query)
        ).first()
        summary_total_selling = float(ref_summary[0]) if ref_summary else 0
        summary_total_cost = float(ref_summary[1]) if ref_summary else 0
        summary_total_pl_result = summary_total_selling - summary_total_cost

        # 余额汇总（售价 - 收款，使用发票分配表正确处理跨项目收款）
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from sqlalchemy import union_all

        # 方式1: 项目级别收款通过发票分配表统计
        summary_alloc = db.session.query(
            func.coalesce(func.sum(ReceiptInvoiceAllocation.allocated_amount), 0)
        ).join(
            ProjectInvoice, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
        ).join(
            ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
        ).filter(
            ProjectInvoice.header_id.in_(filtered_ids_query),
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id == None
        ).scalar() or 0

        # 方式2: REF级别直接收款
        summary_ref_rcpt = db.session.query(
            func.coalesce(func.sum(ProjectReceipt.amount), 0)
        ).filter(
            ProjectReceipt.header_id.in_(filtered_ids_query),
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id.isnot(None)
        ).scalar() or 0

        summary_total_received = float(summary_alloc) + float(summary_ref_rcpt)
        summary_total_balance = summary_total_selling - summary_total_received

        # 按HID数字部分排序（H309 → 309, H1000 → 1000）
        query = query.order_by(func.cast(func.substring(ProjectHeader.hid, 2), db.Integer).asc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        projects = pagination.items

        # 批量获取当前页项目的财务数据（避免N+1）
        project_ids = [p.id for p in projects]
        finance_data = {}
        if project_ids:
            refs_data = db.session.query(
                ProjectRef.header_id,
                func.sum(ProjectRef.selling_price).label('total_selling'),
                func.sum(ProjectRef.cost_price).label('total_cost')
            ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()

            for row in refs_data:
                selling = float(row.total_selling or 0)
                cost = float(row.total_cost or 0)
                finance_data[row.header_id] = {
                    'total_selling': selling,
                    'total_cost': cost,
                    'total_pl': selling - cost,
                    'total_balance': 0  # 下面计算
                }

            # 批量查询收款数据（与项目列表一致，使用发票分配表正确处理跨项目收款）
            from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
            from sqlalchemy import union_all

            # 方式1: 项目级别收款通过发票分配表统计
            alloc_q = db.session.query(
                ProjectInvoice.header_id,
                func.sum(ReceiptInvoiceAllocation.allocated_amount).label('total_alloc')
            ).join(
                ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
            ).join(
                ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
            ).filter(
                ProjectInvoice.header_id.in_(project_ids),
                ProjectReceipt.status == 'confirmed',
                ProjectReceipt.ref_id == None
            ).group_by(ProjectInvoice.header_id).all()

            # 方式2: REF级别直接收款
            ref_rcpt_q = db.session.query(
                ProjectReceipt.header_id,
                func.sum(ProjectReceipt.amount).label('total_direct')
            ).filter(
                ProjectReceipt.header_id.in_(project_ids),
                ProjectReceipt.status == 'confirmed',
                ProjectReceipt.ref_id.isnot(None)
            ).group_by(ProjectReceipt.header_id).all()

            receipt_map = {}
            for row in alloc_q:
                receipt_map[row.header_id] = float(row.total_alloc or 0)
            for row in ref_rcpt_q:
                receipt_map[row.header_id] = receipt_map.get(row.header_id, 0) + float(row.total_direct or 0)

            for pid, data in finance_data.items():
                received = receipt_map.get(pid, 0)
                data['total_balance'] = data['total_selling'] - received

            # 批量查询是否有发票
            invoice_data = db.session.query(
                ProjectInvoice.header_id
            ).filter(
                ProjectInvoice.header_id.in_(project_ids),
                ProjectInvoice.status != 'cancelled'
            ).distinct().all()
            invoiced_ids = {row.header_id for row in invoice_data}
            for pid in project_ids:
                if pid not in finance_data:
                    finance_data[pid] = {'total_selling': 0, 'total_cost': 0, 'total_pl': 0, 'total_balance': 0}
                finance_data[pid]['has_invoice'] = pid in invoiced_ids

            # 批量计算 can_settle 状态
            from App_new.business.projects.models.eo import ProjectEO
            from App_new.business.projects.models.invoice import InvoiceItem

            # REF总数
            ref_counts = db.session.query(
                ProjectRef.header_id,
                func.count(ProjectRef.id).label('ref_count')
            ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()
            ref_count_dict = {r.header_id: r.ref_count for r in ref_counts}

            # 有发票的REF数量
            ref_with_invoice = db.session.query(
                ProjectRef.header_id,
                func.count(db.distinct(InvoiceItem.ref_id)).label('invoiced_ref_count')
            ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id).filter(
                ProjectRef.header_id.in_(project_ids)
            ).group_by(ProjectRef.header_id).all()
            invoiced_ref_dict = {r.header_id: r.invoiced_ref_count for r in ref_with_invoice}

            # EO总数
            eo_counts = db.session.query(
                ProjectRef.header_id,
                func.count(ProjectEO.id).label('eo_count')
            ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
                ProjectRef.header_id.in_(project_ids)
            ).group_by(ProjectRef.header_id).all()
            eo_count_dict = {r.header_id: r.eo_count for r in eo_counts}

            # 已付款EO数量
            eo_paid_counts = db.session.query(
                ProjectRef.header_id,
                func.count(ProjectEO.id).label('paid_eo_count')
            ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id).filter(
                ProjectRef.header_id.in_(project_ids),
                ProjectEO.is_paid == True
            ).group_by(ProjectRef.header_id).all()
            paid_eo_dict = {r.header_id: r.paid_eo_count for r in eo_paid_counts}

            for pid in project_ids:
                ref_count = ref_count_dict.get(pid, 0)
                eo_count = eo_count_dict.get(pid, 0)
                paid_eo_count = paid_eo_dict.get(pid, 0)
                invoiced_ref_count = invoiced_ref_dict.get(pid, 0)
                balance = finance_data[pid].get('total_balance', 0)

                can_settle = (
                    ref_count > 0
                    and ref_count == eo_count
                    and eo_count == paid_eo_count
                    and ref_count == invoiced_ref_count
                    and abs(balance) < 0.01
                )
                finance_data[pid]['can_settle'] = can_settle

        # 统计面板（基于筛选结果）
        total_count = query.count()
        total_profit_result = summary_total_pl_result
        settled_count = query.filter(ProjectHeader.is_settled == True).count()
        unsettled_count = query.filter(ProjectHeader.is_settled == False).count()

        # 获取员工列表（用于筛选下拉和名称解析）
        staff_list = _get_staff_list()
        staff_name_map = _build_staff_name_map(staff_list)

        # 解析每个项目的操作员/业务员显示名称
        project_staff_display = _resolve_project_staff_display(projects, staff_name_map)

        return render_template('finance/athina/athina_performance_settlement.html',
                             projects=projects,
                             finance_data=finance_data,
                             pagination=pagination,
                             search=search,
                             filter_consultant=filter_consultant,
                             filter_sales_consultant=filter_sales_consultant,
                             filter_book_date_from=filter_book_date_from,
                             filter_book_date_to=filter_book_date_to,
                             filter_is_count_performance=filter_is_count_performance,
                             filter_balance=filter_balance,
                             filter_can_settle=filter_can_settle,
                             filter_order_type=filter_order_type,
                             staff_list=staff_list,
                             project_staff_display=project_staff_display,
                             total_count=total_count,
                             total_profit=float(total_profit_result),
                             settled_count=settled_count,
                             unsettled_count=unsettled_count,
                             summary_total_selling=summary_total_selling,
                             summary_total_cost=summary_total_cost,
                             summary_total_pl=float(summary_total_pl_result),
                             summary_total_balance=summary_total_balance,
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
                                       filter_is_count_performance, filter_balance,
                                       filter_can_settle='', filter_order_type=''):
    """构建业绩结算查询的辅助函数（基于ProjectHeader）"""
    from App_new.business.projects.models.project import ProjectHeader, CustomerCompany

    has_filters = (filter_consultant or filter_sales_consultant or
                  filter_book_date_from or filter_book_date_to or
                  filter_is_count_performance != '' or filter_balance != '' or
                  filter_can_settle != '' or filter_order_type != '')

    query = ProjectHeader.query.options(
        db.joinedload(ProjectHeader.company),
        db.joinedload(ProjectHeader.settlement_batch)
    )

    if search and search.strip():
        # 搜索HID或公司名称
        query = query.outerjoin(CustomerCompany, ProjectHeader.company_id == CustomerCompany.id).filter(
            db.or_(
                ProjectHeader.hid.contains(search),
                CustomerCompany.company_name.contains(search)
            )
        )
    elif not has_filters:
        # 无搜索无筛选时，只显示有发票的项目
        from App_new.business.projects.models.invoice import ProjectInvoice
        has_invoice_subquery = db.session.query(ProjectInvoice.header_id).filter(
            ProjectInvoice.status != 'cancelled'
        ).distinct().subquery()
        query = query.filter(ProjectHeader.id.in_(db.select(has_invoice_subquery)))

    # 操作员筛选（通过 operator_ids 匹配员工ID）
    if filter_consultant:
        from sqlalchemy import func as sa_func
        query = query.filter(
            sa_func.find_in_set(str(filter_consultant), ProjectHeader.operator_ids) > 0
        )

    # 业务员筛选（通过 salesperson_ids 匹配员工ID）
    if filter_sales_consultant:
        from sqlalchemy import func as sa_func
        query = query.filter(
            sa_func.find_in_set(str(filter_sales_consultant), ProjectHeader.salesperson_ids) > 0
        )

    # 日期筛选（使用created_at）
    if filter_book_date_from:
        query = query.filter(ProjectHeader.created_at >= filter_book_date_from)

    if filter_book_date_to:
        query = query.filter(ProjectHeader.created_at <= filter_book_date_to + ' 23:59:59')

    # 结算状态筛选
    if filter_is_count_performance != '':
        is_settled = filter_is_count_performance.lower() == 'true'
        query = query.filter(ProjectHeader.is_settled == is_settled)

    # 余额筛选 - 使用发票分配表正确计算收款
    if filter_balance != '':
        from sqlalchemy import func, union_all
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.invoice import ProjectInvoice

        # 子查询：每个项目的总售价
        selling_subq = db.session.query(
            ProjectRef.header_id,
            func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_selling')
        ).group_by(ProjectRef.header_id).subquery()

        # 收款子查询：使用发票分配表正确处理跨项目收款
        invoice_alloc_bal = db.session.query(
            ProjectInvoice.header_id.label('header_id'),
            ReceiptInvoiceAllocation.allocated_amount.label('amount')
        ).join(
            ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
        ).join(
            ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
        ).filter(
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id == None
        )
        ref_rcpt_bal = db.session.query(
            ProjectReceipt.header_id.label('header_id'),
            ProjectReceipt.amount.label('amount')
        ).filter(
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id.isnot(None)
        )
        combined_bal = union_all(invoice_alloc_bal, ref_rcpt_bal).alias('combined_receipts_bal')
        receipt_subq = db.session.query(
            combined_bal.c.header_id,
            func.coalesce(func.sum(combined_bal.c.amount), 0).label('total_received')
        ).group_by(combined_bal.c.header_id).subquery()

        if filter_balance == 'zero_or_negative':
            # 余额 <= 0：收款 >= 售价
            query = query.outerjoin(selling_subq, ProjectHeader.id == selling_subq.c.header_id)\
                         .outerjoin(receipt_subq, ProjectHeader.id == receipt_subq.c.header_id)\
                         .filter(
                             func.coalesce(selling_subq.c.total_selling, 0) - func.coalesce(receipt_subq.c.total_received, 0) <= 0
                         )
        elif filter_balance == 'positive':
            # 余额 > 0：收款 < 售价
            query = query.outerjoin(selling_subq, ProjectHeader.id == selling_subq.c.header_id)\
                         .outerjoin(receipt_subq, ProjectHeader.id == receipt_subq.c.header_id)\
                         .filter(
                             func.coalesce(selling_subq.c.total_selling, 0) - func.coalesce(receipt_subq.c.total_received, 0) > 0
                         )

    # 订单类型筛选
    if filter_order_type:
        query = query.filter(ProjectHeader.order_type == filter_order_type)

    # 可结算状态筛选
    if filter_can_settle != '':
        from sqlalchemy import func, union_all
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.eo import ProjectEO
        from App_new.business.projects.models.invoice import InvoiceItem, ProjectInvoice

        # 子查询：每个项目的REF数
        ref_count_subq = db.session.query(
            ProjectRef.header_id,
            func.count(ProjectRef.id).label('ref_count')
        ).group_by(ProjectRef.header_id).subquery()

        # 子查询：每个项目有发票的REF数
        invoiced_ref_subq = db.session.query(
            ProjectRef.header_id,
            func.count(db.distinct(InvoiceItem.ref_id)).label('inv_ref_count')
        ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id
        ).group_by(ProjectRef.header_id).subquery()

        # 子查询：每个项目的EO数
        eo_count_subq = db.session.query(
            ProjectRef.header_id,
            func.count(ProjectEO.id).label('eo_count')
        ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
        ).group_by(ProjectRef.header_id).subquery()

        # 子查询：每个项目已付款EO数
        paid_eo_subq = db.session.query(
            ProjectRef.header_id,
            func.count(ProjectEO.id).label('paid_count')
        ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
        ).filter(ProjectEO.is_paid == True
        ).group_by(ProjectRef.header_id).subquery()

        # 子查询：每个项目的售价
        sell_subq = db.session.query(
            ProjectRef.header_id,
            func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_sell')
        ).group_by(ProjectRef.header_id).subquery()

        # 收款子查询：使用发票分配表正确处理跨项目收款
        # 方式1: 项目级别收款通过发票分配表统计
        invoice_alloc_q = db.session.query(
            ProjectInvoice.header_id.label('header_id'),
            ReceiptInvoiceAllocation.allocated_amount.label('amount')
        ).join(
            ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
        ).join(
            ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
        ).filter(
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id == None
        )

        # 方式2: REF级别直接收款
        ref_receipt_q = db.session.query(
            ProjectReceipt.header_id.label('header_id'),
            ProjectReceipt.amount.label('amount')
        ).filter(
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id.isnot(None)
        )

        combined = union_all(invoice_alloc_q, ref_receipt_q).alias('combined_receipts')
        rcpt_subq = db.session.query(
            combined.c.header_id,
            func.coalesce(func.sum(combined.c.amount), 0).label('total_rcpt')
        ).group_by(combined.c.header_id).subquery()

        # 可结算项目：ref>0, ref==eo, eo==paid_eo, ref==inv_ref, balance==0
        can_settle_query = db.session.query(ref_count_subq.c.header_id).outerjoin(
            eo_count_subq, ref_count_subq.c.header_id == eo_count_subq.c.header_id
        ).outerjoin(
            paid_eo_subq, ref_count_subq.c.header_id == paid_eo_subq.c.header_id
        ).outerjoin(
            invoiced_ref_subq, ref_count_subq.c.header_id == invoiced_ref_subq.c.header_id
        ).outerjoin(
            sell_subq, ref_count_subq.c.header_id == sell_subq.c.header_id
        ).outerjoin(
            rcpt_subq, ref_count_subq.c.header_id == rcpt_subq.c.header_id
        ).filter(
            ref_count_subq.c.ref_count > 0,
            ref_count_subq.c.ref_count == func.coalesce(eo_count_subq.c.eo_count, 0),
            func.coalesce(eo_count_subq.c.eo_count, 0) == func.coalesce(paid_eo_subq.c.paid_count, 0),
            ref_count_subq.c.ref_count == func.coalesce(invoiced_ref_subq.c.inv_ref_count, 0),
            func.abs(func.coalesce(sell_subq.c.total_sell, 0) - func.coalesce(rcpt_subq.c.total_rcpt, 0)) < 0.01
        ).subquery()

        if filter_can_settle == 'true':
            query = query.filter(ProjectHeader.id.in_(db.select(can_settle_query)))
        else:
            query = query.filter(~ProjectHeader.id.in_(db.select(can_settle_query)))

    return query


@athina_blue.route('/athina_performance_settlement_export', methods=['GET'])
@login_required
@staff_only
def athina_performance_settlement_export():
    """导出业绩结算筛选结果为Excel（基于ProjectHeader）"""
    try:
        from sqlalchemy import func
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.receipt import ProjectReceipt
        from App_new.business.projects.models.invoice import ProjectInvoice

        # 获取筛选参数
        search = request.args.get('search', '')
        filter_consultant = request.args.get('filter_consultant', '')
        filter_sales_consultant = request.args.get('filter_sales_consultant', '')
        filter_book_date_from = request.args.get('filter_book_date_from', '')
        filter_book_date_to = request.args.get('filter_book_date_to', '')
        filter_is_count_performance = request.args.get('filter_is_count_performance', '')
        filter_balance = request.args.get('filter_balance', '')
        filter_can_settle = request.args.get('filter_can_settle', '')
        filter_order_type = request.args.get('filter_order_type', '')

        # 构建查询
        query = build_performance_settlement_query(
            search, filter_consultant, filter_sales_consultant,
            filter_book_date_from, filter_book_date_to,
            filter_is_count_performance, filter_balance,
            filter_can_settle, filter_order_type
        )
        from sqlalchemy import func as sa_func
        query = query.order_by(sa_func.cast(sa_func.substring(ProjectHeader.hid, 2), db.Integer).asc())
        projects = query.all()

        if not projects:
            flash('没有数据可导出', 'warning')
            return redirect(url_for('athina_routes.athina_performance_settlement'))

        # 批量获取财务数据
        project_ids = [p.id for p in projects]
        refs_data = db.session.query(
            ProjectRef.header_id,
            func.sum(ProjectRef.selling_price).label('total_selling'),
            func.sum(ProjectRef.cost_price).label('total_cost')
        ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()
        finance_map = {}
        for row in refs_data:
            finance_map[row.header_id] = {
                'selling': float(row.total_selling or 0),
                'cost': float(row.total_cost or 0)
            }

        receipt_data = db.session.query(
            ProjectReceipt.header_id,
            func.sum(ProjectReceipt.amount).label('total_received')
        ).filter(
            ProjectReceipt.header_id.in_(project_ids),
            ProjectReceipt.status == 'confirmed'
        ).group_by(ProjectReceipt.header_id).all()
        receipt_map = {row.header_id: float(row.total_received or 0) for row in receipt_data}

        invoice_ids = {row.header_id for row in db.session.query(ProjectInvoice.header_id).filter(
            ProjectInvoice.header_id.in_(project_ids), ProjectInvoice.status != 'cancelled'
        ).distinct().all()}

        # 解析操作员/业务员显示名称
        staff_list_export = _get_staff_list()
        staff_name_map_export = _build_staff_name_map(staff_list_export)
        project_staff_display = _resolve_project_staff_display(projects, staff_name_map_export)

        # 准备Excel数据
        data = []
        for project in projects:
            fm = finance_map.get(project.id, {'selling': 0, 'cost': 0})
            received = receipt_map.get(project.id, 0)
            psd = project_staff_display.get(project.id, {})
            data.append({
                'HID': project.hid,
                '公司名称': project.company.company_name if project.company else '',
                '创建日期': project.created_at.strftime('%Y-%m-%d') if project.created_at else '',
                '总金额': fm['selling'],
                '成本': fm['cost'],
                '盈亏': fm['selling'] - fm['cost'],
                '余额': fm['selling'] - received,
                '操作员': psd.get('operator_names', project.operator_names or ''),
                '业务员': psd.get('salesperson_names', project.salesperson_names or ''),
                '是否已开票': '是' if project.id in invoice_ids else '否',
                '是否已核算业绩': '是' if project.is_settled else '否',
                '订单类型': project.order_type or '',
                '操作员利润': float(project.operator_profit) if project.operator_profit else 0.00,
                '业务员利润': float(project.sales_profit) if project.sales_profit else 0.00,
                '公司利润': float(project.company_profit) if project.company_profit else 0.00,
            })

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='业绩结算数据')
            worksheet = writer.sheets['业绩结算数据']
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
    """批量结算（基于ProjectHeader），创建结算单"""
    try:
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.finance.models.settlement_batch import SettlementBatch
        from decimal import Decimal

        data = request.get_json()
        project_ids = data.get('header_ids', [])
        remarks = data.get('remarks', '')

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '请选择要结算的记录'
            }), 400

        projects = ProjectHeader.query.filter(
            ProjectHeader.id.in_(project_ids)
        ).all()

        if len(projects) != len(project_ids):
            return jsonify({
                'success': False,
                'message': '部分记录不存在'
            }), 400

        # 过滤未结算的项目
        unsettled = [p for p in projects if not p.is_settled]
        if not unsettled:
            return jsonify({
                'success': False,
                'message': '所选记录均已结算'
            }), 400

        # 校验所有项目是否满足可结算条件
        from sqlalchemy import func
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.business.projects.models.receipt import ProjectReceipt, ReceiptInvoiceAllocation
        from App_new.business.projects.models.eo import ProjectEO
        from App_new.business.projects.models.invoice import InvoiceItem, ProjectInvoice

        unsettled_ids = [p.id for p in unsettled]

        ref_counts = {r.header_id: r.cnt for r in db.session.query(
            ProjectRef.header_id, func.count(ProjectRef.id).label('cnt')
        ).filter(ProjectRef.header_id.in_(unsettled_ids)).group_by(ProjectRef.header_id).all()}

        invoiced_refs = {r.header_id: r.cnt for r in db.session.query(
            ProjectRef.header_id, func.count(db.distinct(InvoiceItem.ref_id)).label('cnt')
        ).join(InvoiceItem, InvoiceItem.ref_id == ProjectRef.id
        ).filter(ProjectRef.header_id.in_(unsettled_ids)).group_by(ProjectRef.header_id).all()}

        eo_counts = {r.header_id: r.cnt for r in db.session.query(
            ProjectRef.header_id, func.count(ProjectEO.id).label('cnt')
        ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
        ).filter(ProjectRef.header_id.in_(unsettled_ids)).group_by(ProjectRef.header_id).all()}

        paid_eos = {r.header_id: r.cnt for r in db.session.query(
            ProjectRef.header_id, func.count(ProjectEO.id).label('cnt')
        ).join(ProjectRef, ProjectEO.ref_id == ProjectRef.id
        ).filter(ProjectRef.header_id.in_(unsettled_ids), ProjectEO.is_paid == True
        ).group_by(ProjectRef.header_id).all()}

        selling_map = {r.header_id: float(r.total or 0) for r in db.session.query(
            ProjectRef.header_id, func.sum(ProjectRef.selling_price).label('total')
        ).filter(ProjectRef.header_id.in_(unsettled_ids)).group_by(ProjectRef.header_id).all()}

        # 收款计算：使用发票分配表正确处理跨项目收款
        # 方式1: 项目级别收款通过发票分配表统计
        alloc_data = db.session.query(
            ProjectInvoice.header_id,
            func.sum(ReceiptInvoiceAllocation.allocated_amount).label('total')
        ).join(
            ReceiptInvoiceAllocation, ReceiptInvoiceAllocation.invoice_id == ProjectInvoice.id
        ).join(
            ProjectReceipt, ReceiptInvoiceAllocation.receipt_id == ProjectReceipt.id
        ).filter(
            ProjectInvoice.header_id.in_(unsettled_ids),
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id == None
        ).group_by(ProjectInvoice.header_id).all()

        # 方式2: REF级别直接收款
        ref_rcpt_data = db.session.query(
            ProjectReceipt.header_id,
            func.sum(ProjectReceipt.amount).label('total')
        ).filter(
            ProjectReceipt.header_id.in_(unsettled_ids),
            ProjectReceipt.status == 'confirmed',
            ProjectReceipt.ref_id.isnot(None)
        ).group_by(ProjectReceipt.header_id).all()

        receipt_map = {}
        for r in alloc_data:
            receipt_map[r.header_id] = float(r.total or 0)
        for r in ref_rcpt_data:
            receipt_map[r.header_id] = receipt_map.get(r.header_id, 0) + float(r.total or 0)

        cannot_settle = []
        for p in unsettled:
            rc = ref_counts.get(p.id, 0)
            ec = eo_counts.get(p.id, 0)
            pc = paid_eos.get(p.id, 0)
            ic = invoiced_refs.get(p.id, 0)
            balance = selling_map.get(p.id, 0) - receipt_map.get(p.id, 0)
            if not (rc > 0 and rc == ec and ec == pc and rc == ic and abs(balance) < 0.01):
                cannot_settle.append(p.hid)

        if cannot_settle:
            return jsonify({
                'success': False,
                'message': f'以下项目不满足结算条件：{", ".join(cannot_settle)}'
            }), 400

        # 创建结算单
        batch = SettlementBatch()
        batch.batch_number = SettlementBatch.generate_batch_number()
        batch.settled_by = current_user.username if current_user else 'unknown'
        batch.settlement_date = datetime.utcnow()
        batch.remarks = remarks
        db.session.add(batch)
        db.session.flush()

        # 汇总数据
        total_profit = Decimal('0')
        total_operator = Decimal('0')
        total_sales = Decimal('0')
        total_company = Decimal('0')

        for project in unsettled:
            project.is_settled = True
            project.settled_at = datetime.utcnow()
            project.settled_by = current_user.username if current_user else None
            project.settlement_batch_id = batch.id

            total_profit += Decimal(str(project.total_profit or 0))
            total_operator += Decimal(str(project.operator_profit or 0))
            total_sales += Decimal(str(project.sales_profit or 0))
            total_company += Decimal(str(project.company_profit or 0))

        batch.project_count = len(unsettled)
        batch.total_profit = total_profit
        batch.total_operator_profit = total_operator
        batch.total_sales_profit = total_sales
        batch.total_company_profit = total_company

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'结算单 {batch.batch_number} 创建成功，包含 {len(unsettled)} 个项目',
            'count': len(unsettled),
            'batch_number': batch.batch_number,
            'batch_id': batch.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'批量结算失败: {str(e)}'
        }), 500


@athina_blue.route('/athina_batch_settle_all_filtered', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def athina_batch_settle_all_filtered():
    """结算全部筛选结果（跨分页），根据前端传来的筛选参数查询所有匹配项目"""
    try:
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.finance.models.settlement_batch import SettlementBatch
        from decimal import Decimal

        data = request.get_json()
        filters = data.get('filters', {})
        remarks = data.get('remarks', '')

        # 用筛选参数构建查询（与列表页相同逻辑）
        query = build_performance_settlement_query(
            filters.get('search', ''),
            filters.get('filter_consultant', ''),
            filters.get('filter_sales_consultant', ''),
            filters.get('filter_book_date_from', ''),
            filters.get('filter_book_date_to', ''),
            filters.get('filter_is_count_performance', ''),
            filters.get('filter_balance', ''),
            filters.get('filter_can_settle', ''),
            filters.get('filter_order_type', '')
        )

        # 只取未结算的项目ID
        all_ids = [r.id for r in query.filter(
            ProjectHeader.is_settled == False
        ).with_entities(ProjectHeader.id).all()]

        if not all_ids:
            return jsonify({'success': False, 'message': '没有符合条件的未结算项目'}), 400

        # 校验可结算条件
        can_settle_ids = _get_can_settle_project_ids()
        cannot_settle_hids = []
        settleable_ids = []

        projects = ProjectHeader.query.filter(ProjectHeader.id.in_(all_ids)).all()
        for p in projects:
            if p.id in can_settle_ids:
                settleable_ids.append(p)
            else:
                cannot_settle_hids.append(p.hid)

        if not settleable_ids:
            return jsonify({
                'success': False,
                'message': f'没有满足结算条件的项目（{len(cannot_settle_hids)} 个不满足条件）'
            }), 400

        # 创建结算单
        batch = SettlementBatch()
        batch.batch_number = SettlementBatch.generate_batch_number()
        batch.settled_by = current_user.username if current_user else 'unknown'
        batch.settlement_date = datetime.utcnow()
        batch.remarks = remarks
        db.session.add(batch)
        db.session.flush()

        total_profit = Decimal('0')
        total_operator = Decimal('0')
        total_sales = Decimal('0')
        total_company = Decimal('0')

        for project in settleable_ids:
            project.is_settled = True
            project.settled_at = datetime.utcnow()
            project.settled_by = current_user.username if current_user else None
            project.settlement_batch_id = batch.id

            total_profit += Decimal(str(project.total_profit or 0))
            total_operator += Decimal(str(project.operator_profit or 0))
            total_sales += Decimal(str(project.sales_profit or 0))
            total_company += Decimal(str(project.company_profit or 0))

        batch.project_count = len(settleable_ids)
        batch.total_profit = total_profit
        batch.total_operator_profit = total_operator
        batch.total_sales_profit = total_sales
        batch.total_company_profit = total_company

        db.session.commit()

        msg = f'结算单 {batch.batch_number} 创建成功，包含 {len(settleable_ids)} 个项目'
        if cannot_settle_hids:
            msg += f'（跳过 {len(cannot_settle_hids)} 个不满足条件的项目）'

        return jsonify({
            'success': True,
            'message': msg,
            'count': len(settleable_ids),
            'skipped': len(cannot_settle_hids),
            'batch_number': batch.batch_number,
            'batch_id': batch.id
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
    """计算并更新利润分配（仅可结算项目）"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution, get_order_type
        from App_new.business.projects.models.project import ProjectHeader
        from decimal import Decimal

        data = request.get_json()
        project_ids = data.get('header_ids', [])

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '请选择要计算利润分配的记录'
            }), 400

        # 获取可结算项目集合
        can_settle_ids = _get_can_settle_project_ids()

        projects = ProjectHeader.query.filter(
            ProjectHeader.id.in_(project_ids)
        ).all()

        success_count = 0
        skip_count = 0
        error_count = 0
        errors = []

        for project in projects:
            # 跳过不可结算的项目
            if project.id not in can_settle_ids:
                skip_count += 1
                continue
            try:
                # 从REF聚合计算利润
                profit = Decimal(str(project.total_profit))

                order_type = get_order_type(profit)

                if profit == 0:
                    project.operator_profit = Decimal('0')
                    project.sales_profit = Decimal('0')
                    project.company_profit = Decimal('0')
                    project.order_type = order_type
                else:
                    operator_profit, sales_profit, company_profit = calculate_profit_distribution(profit)
                    project.operator_profit = operator_profit
                    project.sales_profit = sales_profit
                    project.company_profit = company_profit
                    project.order_type = order_type

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f'HID {project.hid}: {str(e)}')
                logger.error(f'计算利润分配失败 (HID: {project.hid}): {str(e)}')

        db.session.commit()

        message = f'成功计算 {success_count} 条可结算记录的利润分配'
        if skip_count > 0:
            message += f'，跳过 {skip_count} 条不可结算记录'
        if error_count > 0:
            message += f'，{error_count} 条记录失败'

        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'skip_count': skip_count,
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
    """计算全部可结算的未结算单的利润分配（基于ProjectHeader）"""
    try:
        from App_new.finance.utils.profit_distribution import calculate_profit_distribution, get_order_type
        from App_new.business.projects.models.project import ProjectHeader
        from decimal import Decimal

        # 获取可结算项目集合
        can_settle_ids = _get_can_settle_project_ids()

        # 查询所有未结算且可结算的项目
        projects = ProjectHeader.query.filter(
            ProjectHeader.is_settled == False,
            ProjectHeader.id.in_(can_settle_ids) if can_settle_ids else False
        ).all()

        if not projects:
            return jsonify({
                'success': True,
                'message': '没有找到可结算的未结算单',
                'success_count': 0,
                'error_count': 0
            })

        success_count = 0
        error_count = 0
        errors = []

        for project in projects:
            try:
                profit = Decimal(str(project.total_profit))
                order_type = get_order_type(profit)

                if profit == 0:
                    project.operator_profit = Decimal('0')
                    project.sales_profit = Decimal('0')
                    project.company_profit = Decimal('0')
                    project.order_type = order_type
                else:
                    operator_profit, sales_profit, company_profit = calculate_profit_distribution(profit)
                    project.operator_profit = operator_profit
                    project.sales_profit = sales_profit
                    project.company_profit = company_profit
                    project.order_type = order_type

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f'HID {project.hid}: {str(e)}')
                logger.error(f'计算利润分配失败 (HID: {project.hid}): {str(e)}')

        db.session.commit()

        message = f'成功计算 {success_count} 条可结算未结算单的利润分配'
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


@athina_blue.route('/settlement_batches')
@login_required
@staff_only
def settlement_batch_list():
    """结算单列表页面"""
    from App_new.finance.models.settlement_batch import SettlementBatch

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')

    query = SettlementBatch.query

    if search:
        query = query.filter(
            db.or_(
                SettlementBatch.batch_number.contains(search),
                SettlementBatch.settled_by.contains(search)
            )
        )

    query = query.order_by(SettlementBatch.settlement_date.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    batches = pagination.items

    return render_template('finance/athina/settlement_batch_list.html',
                         batches=batches,
                         pagination=pagination,
                         search=search)


@athina_blue.route('/settlement_batches/<int:batch_id>')
@login_required
@staff_only
def settlement_batch_detail(batch_id):
    """结算单详情页面"""
    from App_new.finance.models.settlement_batch import SettlementBatch
    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from sqlalchemy import func

    batch = SettlementBatch.query.get_or_404(batch_id)

    projects = ProjectHeader.query.options(
        db.joinedload(ProjectHeader.company)
    ).filter(
        ProjectHeader.settlement_batch_id == batch_id
    ).order_by(ProjectHeader.id.asc()).all()

    # 批量获取财务数据
    project_ids = [p.id for p in projects]
    finance_data = {}
    if project_ids:
        refs_data = db.session.query(
            ProjectRef.header_id,
            func.sum(ProjectRef.selling_price).label('total_selling'),
            func.sum(ProjectRef.cost_price).label('total_cost')
        ).filter(ProjectRef.header_id.in_(project_ids)).group_by(ProjectRef.header_id).all()

        for row in refs_data:
            selling = float(row.total_selling or 0)
            cost = float(row.total_cost or 0)
            finance_data[row.header_id] = {
                'total_selling': selling,
                'total_cost': cost,
                'total_pl': selling - cost,
            }

    # 获取员工姓名映射
    staff_name_map = _build_staff_name_map(_get_staff_list())

    # 按员工ID汇总利润分配
    staff_summary = {}
    for p in projects:
        # 操作员利润按人数均分
        op_ids = [int(s.strip()) for s in (p.operator_ids or '').split(',') if s.strip() and s.strip().isdigit()]
        if op_ids and p.operator_profit:
            per_op = float(p.operator_profit) / len(op_ids)
            for uid in op_ids:
                key = f"operator_{uid}"
                if key not in staff_summary:
                    staff_summary[key] = {
                        'name': staff_name_map.get(uid, f'ID:{uid}'),
                        'role': '操作员',
                        'projects': 0,
                        'profit': 0
                    }
                staff_summary[key]['projects'] += 1
                staff_summary[key]['profit'] += per_op

        # 业务员利润按人数均分
        sp_ids = [int(s.strip()) for s in (p.salesperson_ids or '').split(',') if s.strip() and s.strip().isdigit()]
        if sp_ids and p.sales_profit:
            per_sp = float(p.sales_profit) / len(sp_ids)
            for uid in sp_ids:
                key = f"sales_{uid}"
                if key not in staff_summary:
                    staff_summary[key] = {
                        'name': staff_name_map.get(uid, f'ID:{uid}'),
                        'role': '业务员',
                        'projects': 0,
                        'profit': 0
                    }
                staff_summary[key]['projects'] += 1
                staff_summary[key]['profit'] += per_sp

    # 排序：按利润降序
    staff_list = sorted(staff_summary.values(), key=lambda x: -x['profit'])
    # 四舍五入
    for s in staff_list:
        s['profit'] = round(s['profit'], 2)

    # 解析每个项目的操作员/业务员显示名称
    project_staff_display = _resolve_project_staff_display(projects, staff_name_map)

    return render_template('finance/athina/settlement_batch_detail.html',
                         batch=batch,
                         projects=projects,
                         finance_data=finance_data,
                         staff_list=staff_list,
                         project_staff_display=project_staff_display)


@athina_blue.route('/settlement_batches/<int:batch_id>/cancel', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def settlement_batch_cancel(batch_id):
    """撤销结算单"""
    try:
        from App_new.finance.models.settlement_batch import SettlementBatch
        from App_new.business.projects.models.project import ProjectHeader

        batch = SettlementBatch.query.get_or_404(batch_id)
        if batch.status == 'cancelled':
            return jsonify({'success': False, 'message': '该结算单已撤销'}), 400

        # 回退所有关联项目的结算状态
        projects = ProjectHeader.query.filter(
            ProjectHeader.settlement_batch_id == batch_id
        ).all()
        for project in projects:
            project.is_settled = False
            project.settled_at = None
            project.settled_by = None
            project.settlement_batch_id = None

        batch.status = 'cancelled'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'结算单 {batch.batch_number} 已撤销，{len(projects)} 个项目已恢复为未结算'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'撤销失败: {str(e)}'
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


# ==================== Athina 数据导入到项目系统（已废弃） ====================
# athina_to_project, athina_to_project_import, athina_to_project_batch_import 路由已删除
# athina_booking_headers/details 表已废弃，不再从 Athina 表导入数据


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


# athina_to_project_generate_receipt 和 athina_to_project_preview 路由已删除
# （依赖 athina_booking_headers 表，该表已废弃）


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
