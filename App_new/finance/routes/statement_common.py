from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash, send_file
from flask_login import login_required
from App_new.utils.Statement import OriginalStatement
from App_new.utils.Invoice import CountHid
from App_new.exts import db
from App_new.finance.models.statement import BankStatement, BankTransaction
from App_new.finance.models.bank_keywords import BankStatementKeyword
import os
import logging
from App_new.config import Config
import subprocess
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from App_new.exts import csrf
from App_new.utils.decorators import staff_only
from sqlalchemy import desc
from App_new.utils.report_utils import (
    get_report_headers_string,
    read_excel_file,
    read_csv_file,
    compare_profit_columns,
    add_comparison_column
)
from .statement_utils import process_monthly_transactions
# safe_json 已从 Config 类中移除，不再需要

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
statement_common_blue = Blueprint('statement_common_routes', __name__)


@statement_common_blue.route('/open_statement_folder/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def open_statement_folder(bank_name):
    """通用的打开银行文件夹功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
        return redirect(url_for('statement_common_routes.statement_common'))
    
    bank_name = bank_name.upper()
    
    if request.method == 'GET':
        # 根据银行类型重定向到对应的银行页面
        redirect_map = {
            'UOB': url_for('uob_routes.uob_bank'),
            'OCBC': url_for('ocbc_routes.ocbc_bank'),
            'CMB': url_for('cmb_routes.cmb_bank')
        }
        return redirect(redirect_map.get(bank_name, url_for('uob_routes.uob_bank')))
    
    # 设置银行特定的文件夹路径
    folder_paths = {
        'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
        'OCBC': Config.BILLING_DATA_PATH / "OCBC",
        'CMB': Config.BILLING_DATA_PATH / "CMB"
    }
    
    folder_path = folder_paths.get(bank_name)
    
    # 如果文件夹不存在，则创建它
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            flash(f'{bank_name}文件夹不存在，已自动创建', 'info')
        except Exception as e:
            flash(f'创建文件夹失败：{str(e)}', 'error')
            return redirect_to_bank_page(bank_name)
    
    try:
        subprocess.run(['explorer', str(folder_path)], shell=True)
        flash(f'成功打开{bank_name}账单文件夹', 'success')
    except Exception as e:
        flash(f'打开文件夹失败：{str(e)}', 'error')
    
    return redirect_to_bank_page(bank_name)


def redirect_to_bank_page(bank_name):
    """根据银行名称重定向到对应的银行页面"""
    redirect_map = {
        'UOB': url_for('uob_routes.uob_bank'),
        'OCBC': url_for('ocbc_routes.ocbc_bank'),
        'CMB': url_for('cmb_routes.cmb_bank')
    }
    return redirect(redirect_map.get(bank_name, url_for('uob_routes.uob_bank')))



@statement_common_blue.route('/bank_processing/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def bank_processing(bank_name):
    """通用的银行账单处理功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
    return redirect(url_for('uob_routes.uob_bank'))

    bank_name = bank_name.upper()
    
    if request.method == 'GET':
        return redirect_to_bank_page(bank_name)
    
    try:
        # 设置银行特定的文件夹路径
        folder_paths = {
            'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
            'OCBC': Config.BILLING_DATA_PATH / "OCBC",
            'CMB': Config.BILLING_DATA_PATH / "CMB"
        }
        
        folder_path = folder_paths.get(bank_name)
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            flash(f'{bank_name}文件夹不存在，已自动创建', 'info')
        
        if bank_name == 'UOB':
            # UOB银行使用OriginalStatement
            statement = OriginalStatement(str(folder_path))
            statement.statement_process()
            flash('UOB账单整理完成', 'success')
            
        elif bank_name == 'OCBC':
            # OCBC银行处理（暂时使用占位符）
            flash('OCBC账单整理功能尚未实现', 'info')
            
        elif bank_name == 'CMB':
            # CMB银行使用CmbStatement
            from App_new.utils.CmbStatement import CmbStatement
            cmb_processor = CmbStatement(str(folder_path))
            output_file = cmb_processor.statement_process()
            
            # 获取摘要信息
            summary = cmb_processor.get_statement_summary()
            
            if summary:
                flash(f'招商银行账单处理完成！共处理 {summary["total_transactions"]} 笔交易，总金额: {summary["total_amount"]:.2f} CNY', 'success')
            else:
                flash('招商银行账单处理完成！', 'success')
                
    except FileNotFoundError as e:
        flash(f'未找到账单文件：{str(e)}', 'error')
    except Exception as e:
        logger.error(f"{bank_name}银行账单处理失败: {str(e)}")
        flash(f'账单处理失败：{str(e)}', 'error')
    
    return redirect_to_bank_page(bank_name)


@statement_common_blue.route('/original_processing/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def original_processing(bank_name):
    """通用的原始账单处理功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))
    
    bank_name = bank_name.upper()
    
    if request.method == 'GET':
        return redirect_to_bank_page(bank_name)
    
    # 设置银行特定的文件夹路径
    folder_paths = {
        'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
        'OCBC': Config.BILLING_DATA_PATH / "OCBC",
        'CMB': Config.BILLING_DATA_PATH / "CMB"
    }
    
    folder_path = folder_paths.get(bank_name)
    
    if bank_name == 'UOB':
        # UOB银行有完整的原始账单整理功能
        statement = OriginalStatement(str(folder_path))
        statement.organized_statement_data()
        flash('UOB原始账单整理完成', 'success')
    else:
        # OCBC和CMB银行暂时未实现
        flash(f'{bank_name}原始账单整理功能尚未实现', 'info')
    
    return redirect_to_bank_page(bank_name)


# 旧的重复函数已移至通用函数，删除这些重复代码


@statement_common_blue.route('/upload_file/<bank_name>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def upload_file(bank_name):
    """通用的银行文件上传处理函数"""
    try:
        # 验证银行名称
        valid_banks = ['UOB', 'OCBC', 'CMB']
        if bank_name.upper() not in valid_banks:
            return jsonify({'success': False, 'message': f'不支持的银行类型: {bank_name}'})
        
        bank_name = bank_name.upper()
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        if not file.filename.lower().endswith(('.xls', '.xlsx', '.csv')):
            return jsonify({'success': False, 'message': '只支持XLS/XLSX/CSV格式的文件'})
        
        # 获取用户选择的账户名称
        selected_account_name = request.form.get('account_name', '').strip()
        if not selected_account_name:
            return jsonify({'success': False, 'message': '请选择账户名称'})
        
        # 读取文件内容到内存
        import io
        file_content = file.read()
        
        # 根据文件扩展名选择读取方式
        try:
            if file.filename.lower().endswith('.csv'):
                # 读取CSV文件
                print(f"读取CSV文件: {file.filename}")
                try:
                    # 首先尝试UTF-8编码
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                    print("使用UTF-8编码读取CSV成功")
                except UnicodeDecodeError:
                    try:
                        # 如果UTF-8失败，尝试GBK编码
                        df = pd.read_csv(io.BytesIO(file_content), encoding='gbk')
                        print("使用GBK编码读取CSV成功")
                    except UnicodeDecodeError:
                        try:
                            # 如果GBK也失败，尝试GB2312编码
                            df = pd.read_csv(io.BytesIO(file_content), encoding='gb2312')
                            print("使用GB2312编码读取CSV成功")
                        except UnicodeDecodeError:
                            # 最后尝试latin-1编码
                            df = pd.read_csv(io.BytesIO(file_content), encoding='latin-1')
                            print("使用latin-1编码读取CSV成功")
            else:
                # 读取Excel文件
                print(f"读取Excel文件: {file.filename}")
                # 根据银行类型设置跳过行数
                skiprows_map = {
                    'UOB': 7,   # UOB银行账单第8行是header，所以跳过前7行
                    'OCBC': 0,  # OCBC银行账单第1行是header
                    'CMB': 0    # 招商银行账单第1行是header
                }
                target_skiprows = skiprows_map.get(bank_name, 0)
                
                try:
                    # 首先尝试openpyxl引擎
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows, engine='openpyxl')
                    print(f"使用openpyxl引擎，跳过{target_skiprows}行读取成功")
                except Exception as e1:
                    try:
                        # 如果openpyxl失败，尝试xlrd引擎
                        df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows, engine='xlrd')
                        print(f"使用xlrd引擎，跳过{target_skiprows}行读取成功")
                    except Exception as e2:
                        try:
                            # 如果还是失败，尝试不指定引擎
                            df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=target_skiprows)
                            print(f"使用默认引擎，跳过{target_skiprows}行读取成功")
                        except Exception as e3:
                            print(f"所有引擎都失败: openpyxl={e1}, xlrd={e2}, default={e3}")
                            # 最后尝试其他skiprows值
                            for skiprows in [0, 1, 2, 3, 4, 5, 6, 8, 9, 10]:
                                try:
                                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, skiprows=skiprows, engine='openpyxl')
                                    if df is not None and not df.empty and df.shape[1] > 3:
                                        print(f"备用方案：跳过{skiprows}行读取成功")
                                        break
                                except:
                                    continue
            
            if df is None or df.empty:
                return jsonify({
                    'success': False, 
                    'message': f'无法读取文件。请确保文件格式正确，{bank_name}银行账单第1行应该是标题行。'
                })
            
            # 标准化列名
            df.columns = df.columns.astype(str)
            
            # 查找包含日期、描述、金额等关键信息的列
            date_col = None
            desc_col = None
            amount_col = None
            balance_col = None
            account_number_col = None
            account_name_col = None
            
            # OCBC银行特定的字段
            ref_for_account_owner_col = None
            statement_details_info_col = None
            our_ref_col = None
            
            # 调试信息：显示所有列名
            print(f"Excel文件列名: {list(df.columns)}")
            print(f"Excel文件形状: {df.shape}")
            print(f"前几行数据:\n{df.head()}")
            
            for col in df.columns:
                col_lower = str(col).lower().strip()
                print(f"检查列: '{col}' -> '{col_lower}'")
                
                # 日期列识别 - 优先级顺序很重要
                if any(keyword in col_lower for keyword in ['statement value date', 'statement date', 'post date']):
                    date_col = col
                    print(f"找到日期列: {col}")
                elif any(keyword in col_lower for keyword in ['date', '日期', 'transaction date', '交易日期']):
                    date_col = col
                    print(f"找到日期列: {col}")
                
                # 描述列识别
                elif any(keyword in col_lower for keyword in ['for account statement', 'our ref', 'supplementary details']):
                    desc_col = col
                    print(f"找到描述列: {col}")
                elif any(keyword in col_lower for keyword in ['description', '描述', 'transaction description', '交易描述', '摘要']):
                    desc_col = col
                    print(f"找到描述列: {col}")
                
                # 金额列识别 - OCBC有特殊的Debit Amount和Credit Amount列
                elif any(keyword in col_lower for keyword in ['debit amount', 'credit amount']):
                    amount_col = col
                    print(f"找到金额列: {col}")
                elif any(keyword in col_lower for keyword in ['amount', '金额', '交易金额', 'withdrawal', 'deposit', 'amount-cny']):
                    amount_col = col
                    print(f"找到金额列: {col}")
                
                # 余额列识别 - 优先识别Closing Book Balance
                elif any(keyword in col_lower for keyword in ['closing book balance', 'closingbookbalance']):
                    balance_col = col
                    print(f"找到余额列 (Closing Book Balance): {col}")
                elif any(keyword in col_lower for keyword in ['closing available balance', 'opening balance']):
                    balance_col = col
                    print(f"找到余额列: {col}")
                elif any(keyword in col_lower for keyword in ['balance', '余额', '账户余额', 'available balance']):
                    balance_col = col
                    print(f"找到余额列: {col}")
                
                # 账户信息列识别
                elif any(keyword in col_lower for keyword in ['account no', 'account number', 'account#', '账号']):
                    account_number_col = col
                    print(f"找到账户号列: {col}")
                elif any(keyword in col_lower for keyword in ['account name', '账户名称', 'account holder']):
                    account_name_col = col
                    print(f"找到账户名称列: {col}")
                
                # OCBC银行特定字段识别
                elif bank_name == 'OCBC':
                    if any(keyword in col_lower for keyword in ['ref for account owner', 'ref for account']):
                        ref_for_account_owner_col = col
                        print(f"找到Ref For Account Owner列: {col}")
                    elif any(keyword in col_lower for keyword in ['statement details info', 'statement details', 'details info']):
                        statement_details_info_col = col
                        print(f"找到Statement Details Info列: {col}")
                    elif any(keyword in col_lower for keyword in ['our ref', 'our reference']):
                        our_ref_col = col
                        print(f"找到Our Ref列: {col}")
            
            # 如果没有找到明确的列，尝试按位置猜测
            if not date_col and len(df.columns) > 0:
                # 假设第一列是日期
                date_col = df.columns[0]
                print(f"按位置猜测日期列: {date_col}")
            
            if not desc_col and len(df.columns) > 1:
                # 假设第二列是描述
                desc_col = df.columns[1]
                print(f"按位置猜测描述列: {desc_col}")
            
            if not amount_col and len(df.columns) > 2:
                # 查找包含数字的列
                for col in df.columns[2:]:
                    if df[col].dtype in ['int64', 'float64'] or any(pd.notna(val) and str(val).replace('.', '').replace('-', '').isdigit() for val in df[col].head(10)):
                        amount_col = col
                        print(f"按数字类型猜测金额列: {col}")
                        break
            
            print(f"最终识别的列 - 日期: {date_col}, 描述: {desc_col}, 金额: {amount_col}, 余额: {balance_col}")
            print(f"账户信息列 - 账户号: {account_number_col}, 账户名称: {account_name_col}")
            if bank_name == 'OCBC':
                print(f"OCBC特定字段 - Ref For Account Owner: {ref_for_account_owner_col}, Statement Details Info: {statement_details_info_col}, Our Ref: {our_ref_col}")
            
            if not date_col or not desc_col:
                return jsonify({
                    'success': False, 
                    'message': f'Excel文件格式不正确，无法识别必要的列。\n文件列名: {list(df.columns)}\n请确保文件包含日期和描述列。'
                })
            
            # 提取账户信息
            account_number = 'UPLOAD'
            # 优先使用用户选择的账户名称
            account_name = selected_account_name
            
            if account_number_col and account_number_col in df.columns:
                # 获取第一个非空的账户号
                for val in df[account_number_col]:
                    if pd.notna(val) and str(val).strip():
                        account_number = str(val).strip()
                        break
                print(f"提取到账户号: {account_number}")
            
            # 如果用户没有选择账户名称，尝试从文件中提取
            if not account_name or account_name == '上传文件':
                if account_name_col and account_name_col in df.columns:
                    # 获取第一个非空的账户名称
                    for val in df[account_name_col]:
                        if pd.notna(val) and str(val).strip():
                            account_name = str(val).strip()
                            break
                    print(f"从文件提取到账户名称: {account_name}")
                elif bank_name == 'OCBC' and account_number_col:
                    # 对于OCBC银行，如果没有找到账户名称字段，使用Account No.作为账户名称
                    account_name = account_number
                    print(f"OCBC银行使用Account No.作为账户名称: {account_name}")
                elif bank_name == 'UOB' and account_number_col:
                    # 对于UOB银行，如果没有找到账户名称字段，使用Account No.作为账户名称
                    account_name = account_number
                    print(f"UOB银行使用Account No.作为账户名称: {account_name}")
                elif bank_name == 'CMB' and account_number_col:
                    # 对于CMB银行，如果没有找到账户名称字段，使用Account No.作为账户名称
                    account_name = account_number
                    print(f"CMB银行使用Account No.作为账户名称: {account_name}")
            
            print(f"最终使用的账户名称: {account_name}")
            
            # 重命名列 - 根据银行类型处理
            column_mapping = {}
            if date_col:
                column_mapping[date_col] = 'T-Date'
            if desc_col:
                column_mapping[desc_col] = 'Description'
            if balance_col:
                # 对于OCBC银行，保留原始的Closing Book Balance列名
                if bank_name == 'OCBC' and 'closing book balance' in str(balance_col).lower():
                    column_mapping[balance_col] = 'Closing Book Balance'
                else:
                    column_mapping[balance_col] = 'Balance'
            
            # 根据银行类型处理金额列
            if bank_name == 'UOB':
                # UOB银行保留原有的Withdrawal和Deposit列名
                pass
            elif bank_name == 'OCBC':
                # OCBC银行保留原有的Debit Amount和Credit Amount列名
                pass
            else:
                # 其他银行重命名为Amount
                if amount_col:
                    column_mapping[amount_col] = 'Amount'
            
            df = df.rename(columns=column_mapping)
            
            # 检查银行特定的列是否存在
            if bank_name == 'UOB':
                if 'Withdrawal' not in df.columns:
                    print("警告: UOB银行未找到Withdrawal列")
                if 'Deposit' not in df.columns:
                    print("警告: UOB银行未找到Deposit列")
            elif bank_name == 'OCBC':
                if 'Debit Amount' not in df.columns:
                    print("警告: OCBC银行未找到Debit Amount列")
                if 'Credit Amount' not in df.columns:
                    print("警告: OCBC银行未找到Credit Amount列")
            
            # 数据清洗
            print(f"清洗前数据形状: {df.shape}")
            
            # 只删除日期和描述都为空的行
            df = df.dropna(subset=['T-Date', 'Description'])
            print(f"删除空值后数据形状: {df.shape}")
            
            # OCBC银行特殊处理：组合描述字段
            if bank_name == 'OCBC' and (ref_for_account_owner_col or statement_details_info_col or our_ref_col):
                print("开始组合OCBC银行描述字段")
                def combine_ocbc_description(row):
                    parts = []
                    
                    # 添加Ref For Account Owner
                    if ref_for_account_owner_col and ref_for_account_owner_col in df.columns:
                        ref_owner = row[ref_for_account_owner_col]
                        if pd.notna(ref_owner) and str(ref_owner).strip():
                            parts.append(str(ref_owner).strip())
                    
                    # 添加Statement Details Info
                    if statement_details_info_col and statement_details_info_col in df.columns:
                        details_info = row[statement_details_info_col]
                        if pd.notna(details_info) and str(details_info).strip():
                            parts.append(str(details_info).strip())
                    
                    # 添加Our Ref
                    if our_ref_col and our_ref_col in df.columns:
                        our_ref = row[our_ref_col]
                        if pd.notna(our_ref) and str(our_ref).strip():
                            parts.append(str(our_ref).strip())
                    
                    # 组合所有部分
                    combined = ' | '.join(parts)
                    return combined if combined else row.get('Description', '')
                
                # 应用组合函数
                df['Description'] = df.apply(combine_ocbc_description, axis=1)
                print(f"OCBC描述字段组合完成，示例: {df['Description'].head().tolist()}")
            
            # 处理日期 - 根据银行类型使用不同的日期解析逻辑
            try:
                if bank_name == 'CMB':
                    # CMB银行使用MMDD格式，需要特殊处理
                    print("处理CMB银行MMDD格式日期")
                    def parse_cmb_date(date_val):
                        try:
                            if pd.isna(date_val):
                                return None
                            date_str = str(int(float(date_val)))  # 转换为整数再转字符串，去掉小数点
                            if len(date_str) == 4:  # MMDD格式
                                month = int(date_str[:2])
                                day = int(date_str[2:])
                                # 假设年份为当前年份
                                current_year = datetime.now().year
                                return datetime(current_year, month, day).date()
                            elif len(date_str) == 3:  # MDD格式，如825
                                month = int(date_str[0])
                                day = int(date_str[1:])
                                current_year = datetime.now().year
                                return datetime(current_year, month, day).date()
                            else:
                                # 尝试其他格式
                                return pd.to_datetime(date_val, errors='coerce').date()
                        except Exception as e:
                            print(f"CMB日期解析失败: {date_val}, 错误: {e}")
                            return None
                    
                    df['T-Date'] = df['T-Date'].apply(parse_cmb_date)
                    # 删除日期解析失败的行
                    df = df.dropna(subset=['T-Date'])
                    print(f"CMB日期处理后数据形状: {df.shape}")
                elif bank_name == 'OCBC':
                    # OCBC银行使用YYYYMMDD格式，需要特殊处理
                    print("处理OCBC银行YYYYMMDD格式日期")
                    def parse_ocbc_date(date_val):
                        try:
                            if pd.isna(date_val):
                                return None
                            date_str = str(int(float(date_val)))  # 转换为整数再转字符串，去掉小数点
                            if len(date_str) == 8:  # YYYYMMDD格式
                                year = int(date_str[:4])
                                month = int(date_str[4:6])
                                day = int(date_str[6:8])
                                return datetime(year, month, day).date()
                            else:
                                # 尝试其他格式
                                return pd.to_datetime(date_val, errors='coerce').date()
                        except Exception as e:
                            print(f"OCBC日期解析失败: {date_val}, 错误: {e}")
                            return None
                    
                    df['T-Date'] = df['T-Date'].apply(parse_ocbc_date)
                    # 删除日期解析失败的行
                    df = df.dropna(subset=['T-Date'])
                    print(f"OCBC日期处理后数据形状: {df.shape}")
                else:
                    # 其他银行使用标准日期解析
                    df['T-Date'] = pd.to_datetime(df['T-Date'], errors='coerce').dt.date
                    # 删除日期解析失败的行
                    df = df.dropna(subset=['T-Date'])
                    print(f"日期处理后数据形状: {df.shape}")
            except Exception as e:
                print(f"日期处理错误: {e}")
                return jsonify({'success': False, 'message': f'日期格式处理失败: {str(e)}'})
            
            # 创建唯一ID
            try:
                # 确保所有列都是字符串类型
                df['Description'] = df['Description'].astype(str)
                
                # 处理金额列 - 根据银行类型
                if bank_name == 'UOB':
                    # UOB银行有Withdrawal和Deposit两列
                    withdrawal_str = df['Withdrawal'].fillna(0).astype(str) if 'Withdrawal' in df.columns else '0'
                    deposit_str = df['Deposit'].fillna(0).astype(str) if 'Deposit' in df.columns else '0'
                    amount_str = withdrawal_str + '|' + deposit_str
                elif bank_name == 'OCBC':
                    # OCBC银行有Debit Amount和Credit Amount两列
                    debit_str = df['Debit Amount'].fillna(0).astype(str) if 'Debit Amount' in df.columns else '0'
                    credit_str = df['Credit Amount'].fillna(0).astype(str) if 'Credit Amount' in df.columns else '0'
                    amount_str = debit_str + '|' + credit_str
                else:
                    # 其他银行使用Amount列
                    amount_str = df['Amount'].fillna(0).astype(str) if 'Amount' in df.columns else '0'
                
                # 处理余额列 - 针对OCBC银行优先使用Closing Book Balance
                balance_str = '0'
                if bank_name == 'OCBC':
                    # OCBC银行优先使用Closing Book Balance列（用于排重）
                    for balance_col in ['Closing Book Balance', 'Balance', 'Available Balance']:
                        if balance_col in df.columns:
                            balance_str = df[balance_col].fillna('0').astype(str)
                            print(f"OCBC银行使用余额列进行排重: {balance_col}")
                            break
                else:
                    # 其他银行使用Balance列
                    if 'Balance' in df.columns:
                        balance_str = df['Balance'].fillna('0').astype(str)
                    else:
                        balance_str = '0'
                
                # 将T-Date转换为字符串用于ID创建
                df['T-Date-Str'] = df['T-Date'].astype(str)
                
                # 创建复合唯一ID：日期+描述+金额+余额
                df['Id'] = (df['T-Date-Str'] + '|' + df['Description'] + '|' + 
                           amount_str + '|' + balance_str)
                df['Id'] = df['Id'].str.replace('[\s\.\\/]', '', regex=True).str[-50:].str.lower()
                
                print(f"ID创建后数据形状: {df.shape}")
                print(f"示例ID: {df['Id'].head().tolist()}")
            except Exception as e:
                print(f"ID创建错误: {e}")
                return jsonify({'success': False, 'message': f'创建唯一ID失败: {str(e)}'})
            
            # 去除重复数据
            df = df.drop_duplicates(subset=['Id']).reset_index(drop=True)
            print(f"去重后数据形状: {df.shape}")
            
            if df.empty:
                return jsonify({'success': False, 'message': '没有有效的数据可以导入'})
            
            print(f"最终处理的数据样本:\n{df.head()}")
            
            # 按月份分组创建对账单
            # 确保T-Date是datetime类型，如果不是则重新转换
            if df['T-Date'].dtype == 'object':
                df['T-Date'] = pd.to_datetime(df['T-Date'], errors='coerce')
            
            df['Month'] = df['T-Date'].apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else 'Unknown')
            monthly_groups = df.groupby('Month')
            
            print(f"数据按月份分组: {list(monthly_groups.groups.keys())}")
            
            total_processed_count = 0
            statement_numbers = []
            updated_statements = []  # 记录更新的对账单
            
            # 总体关键字统计
            total_keyword_stats = {
                'personal': 0,
                'business': 0,
                'personal_business': 0,
                'no_match': 0,
                'total_keywords_matched': 0
            }
            
            # 设置银行特定的货币
            currency_map = {
                'UOB': 'SGD',
                'OCBC': 'SGD', 
                'CMB': 'CNY'
            }
            currency = currency_map.get(bank_name, 'SGD')
            
            for month, month_data in monthly_groups:
                print(f"处理月份: {month}, 数据行数: {len(month_data)}")

                # 检查该月份该账户是否已有对账单
                # 构造对账单号格式: BANK-账户名-2025-09（账户名取最后4位）
                month_year = month  # 例如: "2025-09"
                # 从账户名称提取简短标识（如取最后4位数字）
                account_suffix = ''.join(filter(str.isdigit, account_name))[-4:] if account_name else 'UNKN'
                expected_statement_number = f"{bank_name}-{account_suffix}-{month_year}"

                # 按银行名称、账户名称和月份查找对账单
                existing_statement = BankStatement.query.filter(
                    BankStatement.bank_name == bank_name,
                    BankStatement.account_name == account_name,
                    BankStatement.statement_number == expected_statement_number
                ).first()

                # 如果用新格式没找到，也尝试旧格式（兼容旧数据）
                if not existing_statement:
                    old_statement_number = f"{bank_name}-{month_year}"
                    existing_statement = BankStatement.query.filter(
                        BankStatement.bank_name == bank_name,
                        BankStatement.account_name == account_name,
                        BankStatement.statement_number == old_statement_number
                    ).first()
                
                if existing_statement:
                    print(f"月份 {month} 已存在对账单: {existing_statement.statement_number}")
                    
                    # 更新对账单的期间，确保覆盖所有数据
                    new_period_start = month_data['T-Date'].min()
                    new_period_end = month_data['T-Date'].max()
                    
                    # 转换为date对象以便比较
                    if hasattr(new_period_start, 'date'):
                        new_period_start = new_period_start.date()
                    if hasattr(new_period_end, 'date'):
                        new_period_end = new_period_end.date()
                    
                    # 如果新数据的开始日期更早，更新period_start
                    if new_period_start < existing_statement.period_start:
                        existing_statement.period_start = new_period_start
                        print(f"更新对账单开始日期: {new_period_start}")
                    
                    # 如果新数据的结束日期更晚，更新period_end
                    if new_period_end > existing_statement.period_end:
                        existing_statement.period_end = new_period_end
                        print(f"更新对账单结束日期: {new_period_end}")
                    
                    # 更新对账单的statement_date为当前日期
                    existing_statement.statement_date = datetime.now().date()
                    print(f"更新对账单日期: {existing_statement.statement_date}")

                    # 更新账户号（如果当前是默认值）
                    if existing_statement.account_number == 'UPLOAD':
                        existing_statement.account_number = account_number
                        print(f"更新对账单账户号: {account_number}")
                    
                    # 记录更新的对账单信息
                    updated_statements.append({
                        'statement_number': existing_statement.statement_number,
                        'period_start': existing_statement.period_start,
                        'period_end': existing_statement.period_end,
                        'account_number': existing_statement.account_number,
                        'account_name': existing_statement.account_name,
                        'updated': True
                    })
                    
                    statement_id = existing_statement.id
                else:
                    # 创建新的对账单记录，使用新格式的对账单号
                    statement_number = expected_statement_number
                    print(f"新对账单号: {statement_number}")
                    # 计算该月的开始和结束日期
                    month_start = month_data['T-Date'].min()
                    month_end = month_data['T-Date'].max()
                    
                    # 设置该月的第一天和最后一天
                    year, month_num = month.split('-')
                    month_start = datetime(int(year), int(month_num), 1).date()
                    
                    # 计算该月的最后一天
                    if int(month_num) == 12:
                        next_month = datetime(int(year) + 1, 1, 1).date()
                    else:
                        next_month = datetime(int(year), int(month_num) + 1, 1).date()
                    
                    month_end = next_month - timedelta(days=1)
                    
                    bank_statement = BankStatement(
                        statement_number=statement_number,
                        bank_name=bank_name,
                        account_number=account_number,
                        account_name=account_name,
                        statement_date=datetime.now().date(),
                        period_start=month_start,
                        period_end=month_end,
                        opening_balance=0.00,
                        closing_balance=0.00,
                        currency=currency,
                        status='draft',
                        created_by='upload'
                    )
                    
                    db.session.add(bank_statement)
                    db.session.flush()  # 获取ID
                    statement_id = bank_statement.id
                    statement_numbers.append(statement_number)
                    
                    # 记录新创建的对账单信息
                    updated_statements.append({
                        'statement_number': statement_number,
                        'period_start': month_start,
                        'period_end': month_end,
                        'account_number': account_number,
                        'account_name': account_name,
                        'updated': False
                    })
                    
                    print(f"创建新对账单: {statement_number}, 期间: {month_start} 到 {month_end}")
                
                # 处理该月份的交易记录
                month_result = process_monthly_transactions(month_data, statement_id, month, bank_name)
                month_processed_count = month_result['processed_count']
                month_keyword_stats = month_result['keyword_stats']
                
                total_processed_count += month_processed_count
                
                # 累计关键字统计
                for key in total_keyword_stats:
                    total_keyword_stats[key] += month_keyword_stats[key]
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'{bank_name}银行文件上传成功！',
                'processed_count': total_processed_count,
                'statement_numbers': statement_numbers,
                'months_processed': list(monthly_groups.groups.keys()),
                'keyword_stats': total_keyword_stats,
                'statement_updates': updated_statements
                })
        except Exception as e:
            db.session.rollback()
            logger.error(f"文件处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'文件处理失败：{str(e)}'})
        
    except Exception as e:
        logger.error(f"{bank_name}银行文件上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'})


@statement_common_blue.route('/update_account_name/<bank_name>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def update_account_name(bank_name):
    """更新对账单的账户名称"""
    try:
        # 验证银行名称
        valid_banks = ['UOB', 'OCBC', 'CMB']
        if bank_name.upper() not in valid_banks:
            return jsonify({'success': False, 'message': f'不支持的银行类型: {bank_name}'})
        
        bank_name = bank_name.upper()
        
        data = request.get_json()
        statement_id = data.get('statement_id')
        account_name = data.get('account_name', '').strip()
        
        if not statement_id:
            return jsonify({'success': False, 'message': '缺少对账单ID'})
        
        if not account_name:
            return jsonify({'success': False, 'message': '账户名称不能为空'})
        
        # 查找对账单
        statement = BankStatement.query.get(statement_id)
        if not statement:
            return jsonify({'success': False, 'message': '对账单不存在'})
        
        # 验证对账单属于指定的银行
        if statement.bank_name != bank_name:
            return jsonify({'success': False, 'message': '对账单不属于指定的银行'})
        
        # 更新账户名称
        statement.account_name = account_name
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '账户名称更新成功',
            'account_name': account_name
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新账户名称失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@statement_common_blue.route('/to_company/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def to_company(bank_name):
    """通用的生成公司账单功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))
    
    bank_name = bank_name.upper()
    
    if request.method == 'GET':
        return redirect_to_bank_page(bank_name)
    
    # 设置银行特定的文件夹路径
    folder_paths = {
        'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
        'OCBC': Config.BILLING_DATA_PATH / "OCBC",
        'CMB': Config.BILLING_DATA_PATH / "CMB"
    }
    
    folder_path = folder_paths.get(bank_name)
    
    if bank_name == 'UOB':
        # UOB银行有完整的公司账单生成功能
        statement = OriginalStatement(str(folder_path))
        statement.statement_to_company()
        flash('UOB公司账单生成完成', 'success')
    else:
        # OCBC和CMB银行暂时未实现
        flash(f'{bank_name}公司账单生成功能尚未实现', 'info')
    
    return redirect_to_bank_page(bank_name)


@statement_common_blue.route('/latest_company_statement/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def latest_company_statement(bank_name):
    """通用的最新公司账单功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
    return redirect(url_for('uob_routes.uob_bank'))

    bank_name = bank_name.upper()

    if request.method == 'GET':
        return redirect_to_bank_page(bank_name)
    
    # 设置银行特定的文件夹路径
    folder_paths = {
        'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
        'OCBC': Config.BILLING_DATA_PATH / "OCBC",
        'CMB': Config.BILLING_DATA_PATH / "CMB"
    }
    
    folder_path = folder_paths.get(bank_name)
    
    if bank_name == 'UOB':
        # UOB银行有完整的公司账单整理功能
        statement = OriginalStatement(str(folder_path))
        statement.latest_company_statement()
        flash('UOB最新公司账单整理完成', 'success')
    else:
        # OCBC和CMB银行暂时未实现
        flash(f'{bank_name}最新公司账单功能尚未实现', 'info')
    
    return redirect_to_bank_page(bank_name)


@statement_common_blue.route('/latest_self_statement/<bank_name>', methods=['GET', 'POST'])
@csrf.exempt
def latest_self_statement(bank_name):
    """通用的最新个人账单功能"""
    # 验证银行名称
    valid_banks = ['UOB', 'OCBC', 'CMB']
    if bank_name.upper() not in valid_banks:
        flash(f'不支持的银行类型: {bank_name}', 'error')
        return redirect(url_for('uob_routes.uob_bank'))
    
    bank_name = bank_name.upper()
    
    if request.method == 'GET':
        return redirect_to_bank_page(bank_name)
    
    # 设置银行特定的文件夹路径
    folder_paths = {
        'UOB': Config.BILLING_DATA_PATH / "ZHANG ZHUAN UOB MASTER",
        'OCBC': Config.BILLING_DATA_PATH / "OCBC",
        'CMB': Config.BILLING_DATA_PATH / "CMB"
    }
    
    folder_path = folder_paths.get(bank_name)
    
    if bank_name == 'UOB':
        # UOB银行有完整的个人账单整理功能
        statement = OriginalStatement(str(folder_path))
        statement.latest_self_statement()
        flash('UOB最新个人账单整理完成', 'success')
    else:
        # OCBC和CMB银行暂时未实现
        flash(f'{bank_name}最新个人账单功能尚未实现', 'info')
    
    return redirect_to_bank_page(bank_name)


@statement_common_blue.route('/download_statement/<bank_name>/<statement_number>')
@login_required
@staff_only
def download_statement(bank_name, statement_number):
    """通用的对账单下载功能"""
    try:
        # 验证银行名称
        valid_banks = ['UOB', 'OCBC', 'CMB']
        if bank_name.upper() not in valid_banks:
            flash(f'不支持的银行类型: {bank_name}', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
        
        bank_name = bank_name.upper()
        
        # 查询对账单
        statement = BankStatement.query.filter(
            BankStatement.bank_name == bank_name,
            BankStatement.statement_number == statement_number
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect_to_bank_page(bank_name)
        
        # 生成Excel文件
        import pandas as pd
        import io
        from datetime import datetime
        
        # 获取交易记录
        transactions = BankTransaction.query.filter(
            BankTransaction.statement_id == statement.id
        ).order_by(BankTransaction.transaction_date.desc()).all()
        
        if not transactions:
            flash(f'对账单 {statement_number} 没有交易记录', 'error')
            return redirect_to_bank_page(bank_name)
        
        # 准备数据
        data = []
        for tx in transactions:
            data.append({
                '交易日期': tx.transaction_date.strftime('%Y-%m-%d') if tx.transaction_date else '',
                '记账日期': tx.post_date.strftime('%Y-%m-%d') if tx.post_date else '',
                '交易类型': '支出' if tx.transaction_type == 'debit' else '收入',
                '交易金额': float(tx.amount) if tx.amount else 0,
                '账户余额': float(tx.balance) if tx.balance else 0,
                '交易摘要': tx.description or '',
                '关键词': tx.keyword or '',
                '归属': tx.owner_label or '',
                'REF/EO': tx.accounting_ref or '',
                '备注': tx.remarks or '',
                '确认状态': '已确认' if tx.is_confirmed else '未确认',
                '确认时间': tx.confirmed_at.strftime('%Y-%m-%d %H:%M') if tx.confirmed_at else '',
                '确认人': tx.confirmed_by or ''
            })
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='交易记录', index=False)
            
            # 获取工作表以设置列宽
            worksheet = writer.sheets['交易记录']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # 生成文件名
        filename = f"{bank_name}_{statement_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"下载对账单失败: {str(e)}")
        flash(f'下载对账单失败：{str(e)}', 'error')
        return redirect_to_bank_page(bank_name)


@statement_common_blue.route('/delete_statement/<bank_name>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def delete_statement(bank_name):
    """通用的对账单删除功能"""
    try:
        # 验证银行名称
        valid_banks = ['UOB', 'OCBC', 'CMB']
        if bank_name.upper() not in valid_banks:
            flash(f'不支持的银行类型: {bank_name}', 'error')
            return redirect(url_for('uob_routes.uob_bank'))
        
        bank_name = bank_name.upper()
        statement_number = request.form.get('statement_number')
        
        if not statement_number:
            flash('缺少对账单号参数', 'error')
            return redirect_to_bank_page(bank_name)
        
        # 查询对账单
        statement = BankStatement.query.filter(
            BankStatement.bank_name == bank_name,
            BankStatement.statement_number == statement_number
        ).first()
        
        if not statement:
            flash(f'对账单 {statement_number} 不存在', 'error')
            return redirect_to_bank_page(bank_name)
        
        # 删除相关交易记录
        BankTransaction.query.filter(BankTransaction.statement_id == statement.id).delete()
        
        # 删除对账单
        db.session.delete(statement)
        db.session.commit()
        
        flash(f'对账单 {statement_number} 已成功删除', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除对账单失败: {str(e)}")
        flash(f'删除对账单失败：{str(e)}', 'error')
    
    return redirect_to_bank_page(bank_name)

