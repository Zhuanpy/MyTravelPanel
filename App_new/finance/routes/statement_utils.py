"""
银行对账单处理共享辅助函数
"""
import pandas as pd
from datetime import datetime
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from App_new.finance.models.bank_keywords import BankStatementKeyword


def analyze_excel_structure(df):
    """分析Excel文件结构"""
    # 标准化列名
    df.columns = df.columns.astype(str)
    all_columns = list(df.columns)
    
    # 识别关键列
    identified_columns = {}
    date_col = None
    desc_col = None
    amount_col = None
    balance_col = None
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        
        if any(keyword in col_lower for keyword in ['date', '日期', 'transaction date', 't-date']):
            date_col = col
        elif any(keyword in col_lower for keyword in ['description', '描述', 'transaction description', 'desc']):
            desc_col = col
        elif any(keyword in col_lower for keyword in ['amount', '金额', 'withdrawal', 'deposit', 'debit', 'credit']):
            amount_col = col
        elif any(keyword in col_lower for keyword in ['balance', '余额', 'available balance', 'bal']):
            balance_col = col
    
    # 按位置猜测
    if not date_col and len(df.columns) > 0:
        date_col = df.columns[0]
    if not desc_col and len(df.columns) > 1:
        desc_col = df.columns[1]
    if not amount_col and len(df.columns) > 2:
        for col in df.columns[2:]:
            if df[col].dtype in ['int64', 'float64'] or any(pd.notna(val) and str(val).replace('.', '').replace('-', '').isdigit() for val in df[col].head(10)):
                amount_col = col
                break
    
    identified_columns = {
        'date': date_col,
        'description': desc_col,
        'amount': amount_col,
        'balance': balance_col
    }
    
    # 数据质量分析
    data_issues = []
    recommendations = []
    
    # 检查空值
    null_counts = df.isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            data_issues.append(f"列 '{col}' 有 {count} 个空值")
    
    # 检查日期列
    if date_col:
        try:
            date_parsed = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = date_parsed.isnull().sum()
            if invalid_dates > 0:
                data_issues.append(f"日期列 '{date_col}' 有 {invalid_dates} 个无效日期")
        except:
            data_issues.append(f"日期列 '{date_col}' 格式无法解析")
    else:
        data_issues.append("未找到日期列")
    
    # 检查描述列
    if not desc_col:
        data_issues.append("未找到描述列")
    
    # 检查金额列
    if not amount_col:
        data_issues.append("未找到金额列")
        recommendations.append("建议手动指定包含交易金额的列")
    
    # 生成建议
    if len(data_issues) == 0:
        recommendations.append("数据结构良好，可以导入")
    else:
        recommendations.append("建议检查并修复数据问题后再导入")
    
    if len(all_columns) > 6:
        recommendations.append("文件包含较多列，建议确认是否需要所有列")
    
    # 准备预览数据（前10行）
    preview_data = []
    for index, row in df.head(10).iterrows():
        row_data = {}
        for col in all_columns:
            value = row[col]
            if pd.isna(value):
                row_data[col] = ''
            else:
                row_data[col] = str(value)
        preview_data.append(row_data)
    
    return {
        'total_rows': len(df),
        'total_columns': len(all_columns),
        'valid_rows': len(df.dropna(subset=[date_col, desc_col]) if date_col and desc_col else df),
        'all_columns': all_columns,
        'identified_columns': identified_columns,
        'preview_data': preview_data,
        'data_issues': data_issues,
        'recommendations': recommendations
    }


def apply_keyword_matching(description, bank_name='UOB'):
    """根据交易描述应用关键字匹配，设置owner标签和关键词"""
    try:
        # 从数据库获取关键字
        keywords = BankStatementKeyword.query.filter(
            BankStatementKeyword.bank_name == bank_name
        ).all()
        
        matched_keywords = []
        owner_label = ''
        
        description_lower = str(description).lower()
        
        for keyword in keywords:
            if keyword.keyword.lower() in description_lower:
                matched_keywords.append(keyword.keyword)
                
                # 根据关键字类型设置owner标签
                if keyword.keyword_type == 'personal':
                    owner_label = '个人消费'
                elif keyword.keyword_type == 'business':
                    owner_label = 'Business'
                elif keyword.keyword_type == 'personal_business':
                    owner_label = '个人商用'
                else:
                    owner_label = 'Business'  # 默认
        
        # 如果没有匹配到关键字，设置默认值
        if not matched_keywords:
            owner_label = 'Business'
        
        return {
            'owner_label': owner_label,
            'matched_keywords': ','.join(matched_keywords) if matched_keywords else '',
            'keyword_count': len(matched_keywords)
        }
        
    except Exception as e:
        print(f"关键字匹配错误: {e}")
        return {
            'owner_label': 'Business',
            'matched_keywords': '',
            'keyword_count': 0
        }


def process_monthly_transactions(month_data, statement_id, month, bank_name='UOB'):
    """处理单个月份的交易记录"""
    processed_count = 0
    error_count = 0
    duplicate_count = 0
    
    # 关键字匹配统计
    keyword_stats = {
        'personal': 0,
        'business': 0,
        'personal_business': 0,
        'no_match': 0,
        'total_keywords_matched': 0
    }
    
    print(f"开始处理月份 {month} 的交易记录，共 {len(month_data)} 条")
    
    for index, row in month_data.iterrows():
        try:
            # 检查是否已存在相同的交易记录
            existing_transaction = BankTransaction.query.filter(
                BankTransaction.tx_fingerprint == row['Id']
            ).first()
            
            if existing_transaction:
                duplicate_count += 1
                print(f"跳过重复记录 {index}: {row['Id']}")
                continue
            
            # 确定交易类型和金额 - 针对不同银行账单结构
            transaction_type = 'debit'
            amount = 0.00
            amount_found = False
            
            # 根据不同银行处理金额列
            if bank_name == 'UOB':
                # UOB银行账单有Withdrawal和Deposit两列
                withdrawal_amount = 0.00
                deposit_amount = 0.00
                
                # 获取Withdrawal金额
                if 'Withdrawal' in row and pd.notna(row['Withdrawal']):
                    try:
                        withdrawal_amount = float(row['Withdrawal'])
                    except (ValueError, TypeError):
                        withdrawal_amount = 0.00
                
                # 获取Deposit金额
                if 'Deposit' in row and pd.notna(row['Deposit']):
                    try:
                        deposit_amount = float(row['Deposit'])
                    except (ValueError, TypeError):
                        deposit_amount = 0.00
                
                # 确定交易类型和金额
                if withdrawal_amount > 0 and deposit_amount == 0:
                    amount = withdrawal_amount
                    transaction_type = 'debit'
                    amount_found = True
                elif deposit_amount > 0 and withdrawal_amount == 0:
                    amount = deposit_amount
                    transaction_type = 'credit'
                    amount_found = True
                elif withdrawal_amount > 0 and deposit_amount > 0:
                    # 两列都有值，取较大的值
                    if withdrawal_amount >= deposit_amount:
                        amount = withdrawal_amount
                        transaction_type = 'debit'
                    else:
                        amount = deposit_amount
                        transaction_type = 'credit'
                    amount_found = True
                    
            else:
                # 其他银行的通用处理逻辑
                if 'Amount' in row and pd.notna(row['Amount']):
                    try:
                        amount = float(row['Amount'])
                        transaction_type = 'debit' if amount < 0 else 'credit'
                        amount = abs(amount)
                        amount_found = True
                    except (ValueError, TypeError):
                        pass
            
            if not amount_found:
                print(f"跳过记录 {index}: 无有效金额")
                continue
            
            # 获取余额
            balance = 0.00
            balance_col_name = None
            
            # 查找余额列
            for col in ['Available Balance', 'Balance', '余额']:
                if col in row and pd.notna(row[col]):
                    balance_col_name = col
                    break
            
            if balance_col_name:
                try:
                    balance = float(row[balance_col_name])
                except (ValueError, TypeError):
                    balance = 0.00
            
            # 应用关键字匹配，设置owner标签
            keyword_result = apply_keyword_matching(row['Description'], bank_name)
            owner_label = keyword_result['owner_label']
            matched_keywords = keyword_result['matched_keywords']
            
            # 统计关键字匹配结果
            if matched_keywords:
                keyword_stats['total_keywords_matched'] += keyword_result['keyword_count']
                if owner_label == '个人消费':
                    keyword_stats['personal'] += 1
                elif owner_label == 'Business':
                    keyword_stats['business'] += 1
                elif owner_label == '个人商用':
                    keyword_stats['personal_business'] += 1
            else:
                keyword_stats['no_match'] += 1
            
            # 创建交易记录
            transaction = BankTransaction(
                statement_id=statement_id,
                transaction_date=row['T-Date'],
                post_date=row['T-Date'],
                transaction_id=row['Id'],
                transaction_type=transaction_type,
                amount=amount,
                balance=balance,
                description=str(row['Description']),
                counterparty_name='',
                reconciliation_status='unmatched',
                is_confirmed=False,
                owner_label=owner_label,
                accounting_ref='',
                remarks='',
                keyword=matched_keywords,
                tx_fingerprint=row['Id'],
                created_at=datetime.utcnow()
            )
            
            db.session.add(transaction)
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"处理记录 {index} 时出错: {e}")
            continue
    
    print(f"月份 {month} 处理完成:")
    print(f"  - 成功处理: {processed_count} 条")
    print(f"  - 跳过重复: {duplicate_count} 条") 
    print(f"  - 处理错误: {error_count} 条")
    print(f"关键字匹配统计:")
    print(f"  - 个人消费: {keyword_stats['personal']} 条")
    print(f"  - 商业用途: {keyword_stats['business']} 条")
    print(f"  - 个人商用: {keyword_stats['personal_business']} 条")
    print(f"  - 无匹配: {keyword_stats['no_match']} 条")
    print(f"  - 总匹配关键字: {keyword_stats['total_keywords_matched']} 个")
    
    return {
        'processed_count': processed_count,
        'keyword_stats': keyword_stats
    }
