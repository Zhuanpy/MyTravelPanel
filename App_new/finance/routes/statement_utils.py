"""
银行对账单处理共享辅助函数
"""
import re
import pandas as pd
from datetime import datetime, date
from App_new.exts import db
from App_new.finance.models.statement import BankTransaction
from App_new.finance.models.bank_keywords import BankStatementKeyword


# 月份英文缩写 -> 月份数字
_MONTH_ABBR = {m: i for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}

# 金额格式: 1,234.56 或 123.45 或带尾部负号 123.45-
_AMOUNT_RE = re.compile(r'^-?[\d,]+\.\d{2}-?$')

# 账单页脚 / 结束标记，遇到则停止追加描述
_FOOTER_RE = re.compile(
    r'(End of Transaction|End of Summary|BALANCE\s*C/F|^Total\b)', re.IGNORECASE)


def _parse_amount(token):
    """将金额字符串转为 float，支持千分位逗号与尾部负号"""
    neg = token.startswith('-') or token.endswith('-')
    value = float(token.strip('-').replace(',', '') or 0)
    return -value if neg else value


def parse_uob_pdf(file_content):
    """
    解析 UOB 银行 PDF 月账单（电子结单 eStatement）。

    UOB 账单交易明细为「定位排版」的多行表格：每笔交易首行包含日期、
    部分描述以及金额/余额，描述可能跨多行延续。本函数依据列的 x 坐标
    （右对齐金额列）将数字归类到 Withdrawals / Deposits / Balance。

    返回 (df, account_number):
      - df 列: ['T-Date', 'Description', 'Withdrawal', 'Deposit', 'Balance']
        与 Excel 上传流程下游所需列保持一致，可直接复用后续处理逻辑。
      - account_number: 从账单中提取的账户号（如 340-305-831-7），无则为 'UPLOAD'
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_content, filetype='pdf')

    # 1. 读取全文，用于提取账单周期（确定年份）与账户号
    full_text = ''.join(page.get_text() for page in doc)

    # 账单周期: "Period: 01 Jan 2026 to 31 Jan 2026"，用于给「DD Mon」补全年份
    start_month = end_month = None
    start_year = end_year = datetime.now().year
    period_match = re.search(
        r'Period:\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+to\s+'
        r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', full_text)
    if period_match:
        start_month, start_year = period_match.group(2), int(period_match.group(3))
        end_month, end_year = period_match.group(5), int(period_match.group(6))

    def year_for(month_abbr):
        # 账单可能跨年（如 12 月到次年 1 月），按月份缩写匹配对应年份
        if month_abbr == end_month:
            return end_year
        if month_abbr == start_month:
            return start_year
        return start_year

    # 账户号: "One Account   340-305-831-7"
    account_number = 'UPLOAD'
    acct_match = re.search(r'(\d{3}-\d{3}-\d{3}-\d)', full_text)
    if acct_match:
        account_number = acct_match.group(1)

    # 2. 逐页解析交易明细
    records = []
    current = None  # 当前正在拼接的交易记录

    for page in doc:
        # 过滤页眉法律声明（y<150）与页脚（y>=740）
        words = [w for w in page.get_text('words') if 150 <= w[1] < 740]
        words.sort(key=lambda w: (w[1], w[0]))

        # 按 y 坐标聚类成行（容差 4px，兼容同一逻辑行被拆成相邻像素的情况）
        lines = []
        for w in words:
            if lines and abs(w[1] - lines[-1][0]) <= 4:
                lines[-1][1].append(w)
            else:
                lines.append([w[1], [w]])

        for _y, tokens in lines:
            tokens.sort(key=lambda t: t[0])  # 行内按 x 从左到右

            # 识别日期 token（最左侧的「日」数字 + 月份缩写）
            day = month = None
            used = set()
            for idx, t in enumerate(tokens):
                x0, word = t[0], t[4]
                if day is None and x0 < 70 and word.isdigit() and 1 <= int(word) <= 31:
                    day = int(word)
                    used.add(idx)
                elif day is not None and month is None and x0 < 95 and word in _MONTH_ABBR:
                    month = word
                    used.add(idx)

            # 解析金额/余额（按右边缘 x1 归类到对应列）与描述
            withdrawal = deposit = balance = None
            desc_parts = []
            for idx, t in enumerate(tokens):
                if idx in used:
                    continue
                x0, x1, word = t[0], t[2], t[4]
                if _AMOUNT_RE.match(word):
                    if 343 < x1 <= 405:        # Withdrawals 列（右对齐约 387）
                        withdrawal = _parse_amount(word)
                    elif 405 < x1 <= 495:      # Deposits 列（右对齐约 466）
                        deposit = _parse_amount(word)
                    elif 495 < x1 <= 565:      # Balance 列（右对齐约 546）
                        balance = _parse_amount(word)
                    elif x0 >= 110:            # 描述区内的数字（如外币 TWD 1000.00）
                        desc_parts.append(word)
                elif x0 >= 110:
                    desc_parts.append(word)

            desc_text = ' '.join(desc_parts).strip()

            if day is not None and month is not None:
                # 新交易行
                if current:
                    records.append(current)
                current = {
                    'day': day, 'month': month,
                    'desc': desc_parts,
                    'withdrawal': withdrawal,
                    'deposit': deposit,
                    'balance': balance,
                }
            else:
                # 描述延续行：遇到页脚/汇总标记则结束当前交易
                if current is None:
                    continue
                if desc_text and _FOOTER_RE.search(desc_text):
                    records.append(current)
                    current = None
                    continue
                if desc_parts:
                    current['desc'].extend(desc_parts)

        if current:
            records.append(current)
            current = None

    # 3. 组装为 DataFrame（跳过 BALANCE B/F / C/F 等无收支的余额行）
    rows = []
    for r in records:
        if r['withdrawal'] is None and r['deposit'] is None:
            continue
        try:
            t_date = date(year_for(r['month']), _MONTH_ABBR[r['month']], r['day'])
        except (ValueError, KeyError):
            continue
        rows.append({
            'T-Date': t_date,
            'Description': ' '.join(r['desc']).strip(),
            'Withdrawal': r['withdrawal'],
            'Deposit': r['deposit'],
            'Balance': r['balance'],
        })

    df = pd.DataFrame(rows, columns=['T-Date', 'Description', 'Withdrawal', 'Deposit', 'Balance'])
    return df, account_number


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
    """根据交易描述应用关键字匹配，设置owner标签和关键词

    返回的 auto_confirm 为 True 表示命中了 bank_charge（银行费用）类关键字：
    手续费、TRANS CHARGE、CASH REBATE 这类流水是银行自身产生的，没有对手方，
    永远匹配不到 REF/EO/收款单，需要在导入时直接确认，否则每期都会挂着未确认
    把对账单一直摁在「进行中」。
    """
    try:
        # 从数据库获取关键字
        keywords = BankStatementKeyword.query.filter(
            BankStatementKeyword.bank_name == bank_name
        ).all()
        
        print(f"关键字匹配调试 - 银行: {bank_name}, 描述: {description}")
        print(f"找到 {len(keywords)} 个关键字配置")
        
        # 打印所有关键字配置
        for kw in keywords:
            print(f"  - 关键字: {kw.keyword}, 类型: {kw.keyword_type}, 激活: {kw.is_active}")
        
        matched_keywords = []
        owner_label = ''
        auto_confirm = False      # 命中银行费用类关键字 → 导入时直接确认
        charge_keywords = []      # 命中的银行费用关键字（写入备注便于追溯）

        description_lower = str(description).lower()
        
        for keyword in keywords:
            if not keyword.is_active:
                print(f"跳过非激活关键字: {keyword.keyword}")
                continue
                
            print(f"检查关键字: {keyword.keyword} (类型: {keyword.keyword_type})")
            if keyword.keyword.lower() in description_lower:
                matched_keywords.append(keyword.keyword)
                print(f"匹配到关键字: {keyword.keyword}")
                
                # 根据关键字类型设置owner标签
                if keyword.keyword_type == 'personal':
                    owner_label = '个人消费'
                elif keyword.keyword_type == 'business':
                    owner_label = 'Business'
                elif keyword.keyword_type == 'personal_business':
                    owner_label = '个人商用'
                elif keyword.keyword_type == 'je':
                    owner_label = 'JE'
                    print(f"警告: 匹配到 'je' 类型关键字，设置 owner_label 为 'JE'")
                elif keyword.keyword_type == 'bank_charge':
                    # 银行费用/返现：不动归属标签（沿用其他关键字或默认值），只标记可自动确认
                    auto_confirm = True
                    charge_keywords.append(keyword.keyword)
                    print(f"匹配到银行费用关键字: {keyword.keyword}，该笔导入后自动确认")
                else:
                    owner_label = 'Business'  # 默认
        
        # 没匹配到关键字，或只匹配到不设归属的 bank_charge → 用默认归属，避免留空
        if not matched_keywords or not owner_label:
            # 为不同银行设置不同的默认值
            if bank_name == 'OCBC':
                owner_label = 'JE'  # OCBC 是公司账户，默认使用 JE
            else:
                owner_label = 'Business'
            print(f"无归属类关键字匹配，使用默认值: {owner_label}")
        else:
            print(f"匹配到关键字，设置owner_label: {owner_label}")
            
        # OCBC 银行强制使用 'JE' 作为默认值（公司账户）
        if bank_name == 'OCBC':
            owner_label = 'JE'
            print(f"OCBC 银行强制设置 owner_label 为 'JE'（公司账户）")
        
        return {
            'owner_label': owner_label,
            'matched_keywords': ','.join(matched_keywords) if matched_keywords else '',
            'keyword_count': len(matched_keywords),
            'auto_confirm': auto_confirm,
            'charge_keywords': ','.join(charge_keywords) if charge_keywords else ''
        }

    except Exception as e:
        print(f"关键字匹配错误: {e}")
        return {
            'owner_label': 'Business',
            'matched_keywords': '',
            'keyword_count': 0,
            'auto_confirm': False,
            'charge_keywords': ''
        }


def process_monthly_transactions(month_data, statement_id, month, bank_name='UOB'):
    """处理单个月份的交易记录"""
    processed_count = 0
    error_count = 0
    duplicate_count = 0
    confirmed_duplicate_count = 0
    unconfirmed_duplicate_count = 0
    
    # 关键字匹配统计
    keyword_stats = {
        'personal': 0,
        'business': 0,
        'personal_business': 0,
        'no_match': 0,
        'total_keywords_matched': 0,
        'auto_confirmed': 0
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
                # 根据确认状态给出不同的提示信息并统计
                if existing_transaction.is_confirmed:
                    confirmed_duplicate_count += 1
                    print(f"跳过已确认的重复记录 {index}: {row['Id']} (确认时间: {existing_transaction.confirmed_at})")
                else:
                    unconfirmed_duplicate_count += 1
                    print(f"跳过未确认的重复记录 {index}: {row['Id']}")
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
                    
            elif bank_name == 'OCBC':
                # OCBC银行账单有Debit Amount和Credit Amount两列
                debit_amount = 0.00
                credit_amount = 0.00
                
                # 获取Debit Amount金额
                if 'Debit Amount' in row and pd.notna(row['Debit Amount']):
                    try:
                        debit_amount = float(row['Debit Amount'])
                    except (ValueError, TypeError):
                        debit_amount = 0.00
                
                # 获取Credit Amount金额
                if 'Credit Amount' in row and pd.notna(row['Credit Amount']):
                    try:
                        credit_amount = float(row['Credit Amount'])
                    except (ValueError, TypeError):
                        credit_amount = 0.00
                
                # 确定交易类型和金额
                if debit_amount > 0 and credit_amount == 0:
                    amount = debit_amount
                    transaction_type = 'debit'
                    amount_found = True
                elif credit_amount > 0 and debit_amount == 0:
                    amount = credit_amount
                    transaction_type = 'credit'
                    amount_found = True
                elif debit_amount > 0 and credit_amount > 0:
                    # 两列都有值，取较大的值
                    if debit_amount >= credit_amount:
                        amount = debit_amount
                        transaction_type = 'debit'
                    else:
                        amount = credit_amount
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
            
            # 查找余额列 - 针对OCBC银行优先使用Closing Book Balance
            if bank_name == 'OCBC':
                # OCBC银行优先使用Closing Book Balance作为余额
                for col in ['Closing Book Balance', 'Available Balance', 'Balance', '余额']:
                    if col in row and pd.notna(row[col]):
                        balance_col_name = col
                        break
            else:
                # 其他银行使用通用余额列
                for col in ['Available Balance', 'Balance', '余额']:
                    if col in row and pd.notna(row[col]):
                        balance_col_name = col
                        break
            
            if balance_col_name:
                try:
                    balance = float(row[balance_col_name])
                    print(f"使用余额列: {balance_col_name}, 余额值: {balance}")
                except (ValueError, TypeError):
                    balance = 0.00
                    print(f"余额列 {balance_col_name} 转换失败，使用默认值 0.00")
            else:
                print(f"未找到有效的余额列，使用默认值 0.00")
            
            # 应用关键字匹配，设置owner标签
            keyword_result = apply_keyword_matching(row['Description'], bank_name)
            owner_label = keyword_result['owner_label']
            matched_keywords = keyword_result['matched_keywords']
            # 银行费用/返现类流水没有对手方，导入即确认并标记已核对，
            # 否则每期都会剩几笔未确认，把对账单永远摁在「进行中」
            auto_confirm = keyword_result.get('auto_confirm', False)
            now = datetime.utcnow()

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
                is_confirmed=auto_confirm,
                confirmed_at=now if auto_confirm else None,
                confirmed_by='auto' if auto_confirm else None,
                is_reconciled=auto_confirm,
                reconciled_at=now if auto_confirm else None,
                reconciled_by='auto' if auto_confirm else None,
                owner_label=owner_label,
                accounting_ref='',
                remarks=f"银行费用自动确认（{keyword_result.get('charge_keywords', '')}）" if auto_confirm else '',
                keyword=matched_keywords,
                tx_fingerprint=row['Id'],
                created_at=now
            )

            db.session.add(transaction)
            processed_count += 1
            if auto_confirm:
                keyword_stats['auto_confirmed'] += 1
            
        except Exception as e:
            error_count += 1
            print(f"处理记录 {index} 时出错: {e}")
            continue
    
    print(f"月份 {month} 处理完成:")
    print(f"  - 成功处理: {processed_count} 条")
    print(f"  - 跳过重复: {duplicate_count} 条")
    print(f"    - 已确认重复: {confirmed_duplicate_count} 条")
    print(f"    - 未确认重复: {unconfirmed_duplicate_count} 条")
    print(f"  - 处理错误: {error_count} 条")
    print(f"关键字匹配统计:")
    print(f"  - 个人消费: {keyword_stats['personal']} 条")
    print(f"  - 商业用途: {keyword_stats['business']} 条")
    print(f"  - 个人商用: {keyword_stats['personal_business']} 条")
    print(f"  - 无匹配: {keyword_stats['no_match']} 条")
    print(f"  - 总匹配关键字: {keyword_stats['total_keywords_matched']} 个")
    print(f"  - 银行费用自动确认: {keyword_stats['auto_confirmed']} 条")
    
    return {
        'processed_count': processed_count,
        'duplicate_count': duplicate_count,
        'confirmed_duplicate_count': confirmed_duplicate_count,
        'unconfirmed_duplicate_count': unconfirmed_duplicate_count,
        'error_count': error_count,
        'keyword_stats': keyword_stats
    }
