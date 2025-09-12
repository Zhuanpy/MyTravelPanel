import os
import pandas as pd
import logging
from pathlib import Path

pd.set_option('display.max_columns', None)

class CmbStatement:
    """招商银行账单处理类"""
    
    def __init__(self, cmb_path: str):
        self.file_path = Path(cmb_path)
        self.expense_category = ["个人消费", "个人商用", "LG", "JE"]
        
    def read_original_file(self):
        """读取招商银行原始账单文件"""
        try:
            # 查找CMB文件夹中的Excel文件
            excel_files = []
            for file_path in self.file_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.xls', '.xlsx']:
                    excel_files.append(file_path)
            
            if not excel_files:
                raise FileNotFoundError("CMB文件夹中没有找到Excel文件")
            
            # 使用最新的文件
            latest_file = max(excel_files, key=lambda x: x.stat().st_mtime)
            logging.info(f"使用文件: {latest_file}")
            
            # 读取Excel文件
            try:
                # 尝试不同的读取方式
                df = pd.read_excel(latest_file, engine='openpyxl')
            except:
                try:
                    df = pd.read_excel(latest_file, engine='xlrd')
                except:
                    df = pd.read_excel(latest_file)
            
            # 标准化列名
            df = self._standardize_columns(df)
            
            # 处理数据
            df = self._process_data(df)
            
            return df
            
        except Exception as e:
            logging.error(f"读取招商银行文件失败: {str(e)}")
            raise e
    
    def _standardize_columns(self, df):
        """标准化列名"""
        # 创建列名映射
        column_mapping = {}
        
        for col in df.columns:
            col_str = str(col).strip()
            
            # 日期相关
            if any(keyword in col_str for keyword in ['日期', 'date', 'Date', '交易日期']):
                column_mapping[col] = 'transaction_date'
            elif any(keyword in col_str for keyword in ['记账日期', 'post_date', 'Post Date']):
                column_mapping[col] = 'post_date'
            
            # 金额相关
            elif any(keyword in col_str for keyword in ['金额', 'amount', 'Amount', '交易金额']):
                column_mapping[col] = 'amount'
            elif any(keyword in col_str for keyword in ['余额', 'balance', 'Balance', '账户余额']):
                column_mapping[col] = 'balance'
            
            # 描述相关
            elif any(keyword in col_str for keyword in ['摘要', 'description', 'Description', '交易摘要', '备注']):
                column_mapping[col] = 'description'
            elif any(keyword in col_str for keyword in ['关键词', 'keyword', 'Keyword', '分类']):
                column_mapping[col] = 'keyword'
            
            # 类型相关
            elif any(keyword in col_str for keyword in ['类型', 'type', 'Type', '交易类型']):
                column_mapping[col] = 'transaction_type'
            
            # 对方信息
            elif any(keyword in col_str for keyword in ['对方', 'counterparty', 'Counterparty', '对方户名']):
                column_mapping[col] = 'counterparty'
        
        # 应用列名映射
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _process_data(self, df):
        """处理数据"""
        try:
            # 确保必要的列存在
            required_columns = ['transaction_date', 'amount', 'description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"缺少必要的列: {missing_columns}")
            
            # 处理日期
            if 'transaction_date' in df.columns:
                df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce').dt.date
            
            if 'post_date' in df.columns:
                df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce').dt.date
            
            # 处理金额
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                # 根据金额正负判断交易类型
                df['transaction_type'] = df['amount'].apply(lambda x: 'credit' if x > 0 else 'debit')
            
            # 处理余额
            if 'balance' in df.columns:
                df['balance'] = pd.to_numeric(df['balance'], errors='coerce')
            
            # 处理描述
            if 'description' in df.columns:
                df['description'] = df['description'].astype(str).fillna('')
            
            # 创建唯一ID
            df['id'] = (df['description'].astype(str) + 
                       df['amount'].astype(str) + 
                       df['transaction_date'].astype(str))
            df['id'] = df['id'].str.replace('[\s\.\\/]', '', regex=True).str[-20:].str.lower()
            
            # 去除重复数据
            df = df.drop_duplicates(subset=['id']).reset_index(drop=True)
            
            # 添加默认值
            df['bank_name'] = '招商银行'
            df['account_name'] = '招商银行账户'
            df['currency'] = 'CNY'
            df['owner_label'] = ''
            df['accounting_ref'] = ''
            df['remarks'] = ''
            
            return df
            
        except Exception as e:
            logging.error(f"处理招商银行数据失败: {str(e)}")
            raise e
    
    def statement_process(self):
        """处理招商银行账单"""
        try:
            # 读取原始文件
            df = self.read_original_file()
            
            # 保存处理后的数据
            output_path = self.file_path / "processed"
            output_path.mkdir(exist_ok=True)
            
            # 生成文件名
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"cmb_processed_{timestamp}.xlsx"
            
            # 保存为Excel文件
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            logging.info(f"招商银行账单处理完成，保存至: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logging.error(f"招商银行账单处理失败: {str(e)}")
            raise e
    
    def get_statement_summary(self):
        """获取账单摘要信息"""
        try:
            df = self.read_original_file()
            
            summary = {
                'total_transactions': len(df),
                'total_amount': df['amount'].sum() if 'amount' in df.columns else 0,
                'credit_amount': df[df['transaction_type'] == 'credit']['amount'].sum() if 'transaction_type' in df.columns else 0,
                'debit_amount': abs(df[df['transaction_type'] == 'debit']['amount'].sum()) if 'transaction_type' in df.columns else 0,
                'date_range': {
                    'start': df['transaction_date'].min() if 'transaction_date' in df.columns else None,
                    'end': df['transaction_date'].max() if 'transaction_date' in df.columns else None
                }
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"获取招商银行账单摘要失败: {str(e)}")
            return None
