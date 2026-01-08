# -*- coding: utf-8 -*-
"""
Athina 账单导入服务 - 优化版本
支持CSV预处理，简化数据导入逻辑
"""

import pandas as pd
import traceback
from decimal import Decimal
from datetime import datetime
from App_new.exts import db
from App_new.finance.models.athina_booking import AthinaBookingHeader, AthinaBookingDetail


class AthinaImportService:
    """Athina账单导入服务"""
    
    def __init__(self):
        self.required_columns = [
            'Corporate Name', 'Client Name', 'Booking Ref', 'Book Type', 
            'Book Date', 'Dep Date', 'Itin Desc', 'Gross Curr', 'Gross', 
            'Gross Tax', 'Disc', 'Local Gross', 'Local Cost', 'PL', 'Marg', 
            'Balance', 'Supplier', 'Consultant', 'Sales Consultant', 
            'Invoice No', 'Invoice Date'
        ]
        
        # 列名映射，处理不同的列名格式
        self.column_mapping = {
            'Corporate Name': ['Corporate Name', 'Corporate', 'Company'],
            'Client Name': ['Client Name', 'Client Nam', 'Client'],
            'Booking Ref': ['Booking Ref', 'Booking Re', 'Ref', 'Reference'],
            'Book Type': ['Book Type', 'Type'],
            'Book Date': ['Book Date', 'Booking Date'],
            'Dep Date': ['Dep Date', 'Departure Date', 'Dep'],
            'Itin Desc': ['Itin Desc', 'Itinerary', 'Description'],
            'Gross Curr': ['Gross Curr', 'Currency', 'Curr'],
            'Gross': ['Gross', 'Gross Amount'],
            'Gross Tax': ['Gross Tax', 'Tax'],
            'Disc': ['Disc', 'Discount'],
            'Local Gross': ['Local Gross', 'Local'],
            'Local Cost': ['Local Cost', 'Cost'],
            'PL': ['PL', 'Profit Loss', 'P&L'],
            'Marg': ['Marg', 'Margin'],
            'Balance': ['Balance'],
            'Supplier': ['Supplier'],
            'Consultant': ['Consultant'],
            'Sales Consultant': ['Sales Consultant', 'Sales Consu'],
            'Invoice No': ['Invoice No', 'Invoice'],
            'Invoice Date': ['Invoice Date', 'Invoice Date']
        }
    
    def preprocess_csv(self, file_path):
        """预处理CSV文件"""
        try:
            print("=" * 50)
            print("开始预处理CSV文件...")
            
            # 尝试多种编码读取CSV文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    print(f"尝试使用 {encoding} 编码读取文件...")
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"使用 {encoding} 编码读取成功，行数: {len(df)}, 列数: {len(df.columns)}")
                    break
                except UnicodeDecodeError as e:
                    print(f"使用 {encoding} 编码失败: {e}")
                    continue
            
            if df is None:
                return None
            
            print(f"\n原始数据预览:")
            print(df.head(10).to_string())
            
            # 步骤1：第一列 Booking Header 向下填充
            print(f"\n步骤1：处理Booking Header列...")
            if len(df.columns) > 0:
                # 找到包含"Booking Header:"的行
                booking_header_mask = df.iloc[:, 0].astype(str).str.contains('Booking Header:', na=False)
                print(f"找到 {booking_header_mask.sum()} 个Booking Header行")
                
                # 提取Booking Header ID并向下填充
                df.iloc[:, 0] = df.iloc[:, 0].astype(str)
                df.iloc[:, 0] = df.iloc[:, 0].str.extract(r'Booking Header:\s*(\d+)')[0]
                df.iloc[:, 0] = df.iloc[:, 0].ffill()
                print(f"Booking Header列填充完成")
            
            # 步骤1.5：修正第2列的公司名称
            print(f"\n步骤1.5：修正第2列的公司名称...")
            if len(df.columns) > 1:
                # 将第2列重命名为Corporate Name
                df.columns = [df.columns[0]] + ['Corporate Name'] + list(df.columns[2:])
                print(f"第2列已重命名为Corporate Name")
                
                # 从第2列中提取公司名称（如果存在）
                for idx, row in df.iterrows():
                    if pd.isna(row.iloc[1]) or str(row.iloc[1]).strip() == 'nan':
                        # 如果第2列为空，尝试从第1列提取公司名称
                        if 'Booking Header:' in str(row.iloc[0]):
                            # 从Booking Header行中提取公司名称
                            header_text = str(row.iloc[0])
                            if 'Booking Header:' in header_text:
                                # 提取Booking Header后的公司名称部分
                                parts = header_text.split('Booking Header:')
                                if len(parts) > 1:
                                    company_part = parts[1].strip()
                                    if company_part and not company_part.isdigit():
                                        df.iloc[idx, 1] = company_part
                                        print(f"从Booking Header行提取公司名称: {company_part}")
                    else:
                        # 如果第2列有值，保留它
                        company_name = str(row.iloc[1]).strip()
                        if company_name and company_name != 'nan':
                            print(f"保留第2列的公司名称: {company_name}")
            
            # 步骤2：去掉第2列（Corporate Name）和Itin Desc列都为空的行
            print(f"\n步骤2：过滤空行...")
            original_rows = len(df)
            
            # 找到Itin Desc列（通常是第7列，索引为6）
            itin_desc_col = None
            for i, col in enumerate(df.columns):
                if 'Itin Desc' in str(col) or 'Itinerary' in str(col):
                    itin_desc_col = i
                    break
            
            if itin_desc_col is not None:
                # 过滤条件：第2列（索引1）和Itin Desc列都为空的行
                mask = ~((df.iloc[:, 1].isna() | (df.iloc[:, 1].astype(str).str.strip() == '')) & 
                        (df.iloc[:, itin_desc_col].isna() | (df.iloc[:, itin_desc_col].astype(str).str.strip() == '')))
                df = df[mask].reset_index(drop=True)
                print(f"过滤掉 {original_rows - len(df)} 行空数据，剩余 {len(df)} 行")
            else:
                print("未找到Itin Desc列，跳过空行过滤")
            
            # 步骤3：重新命名列，因为预处理后数据结构已改变
            print(f"\n步骤3：重新命名列...")
            if len(df.columns) >= 2:
                # 第一列现在是booking_header_id，第二列已经是Corporate Name
                new_columns = ['booking_header_id'] + list(df.columns[1:])
                df.columns = new_columns
                print(f"列名已更新: {list(df.columns)}")
            
            print(f"\n预处理后数据预览:")
            print(df.head(10).to_string())
            
            print(f"\n预处理完成！")
            print(f"原始行数: {original_rows}")
            print(f"处理后行数: {len(df)}")
            
            return df
            
        except Exception as e:
            print(f"预处理CSV文件时出错: {str(e)}")
            import traceback
            print(f"错误详情: {traceback.format_exc()}")
            return None
    
    def map_columns(self, columns):
        """映射列名到标准名称"""
        mapped = {}
        missing = []
        
        # 预处理后的列结构：第一列是booking_header_id，第二列是Corporate Name
        # 所以我们需要调整映射逻辑
        for standard_name, variations in self.column_mapping.items():
            found = False
            for col in columns:
                if any(var.lower() in col.lower() for var in variations):
                    mapped[standard_name] = col
                    found = True
                    break
            if not found:
                missing.append(standard_name)
        
        # 特殊处理：booking_header_id 列
        if 'booking_header_id' in columns:
            mapped['Booking Header ID'] = 'booking_header_id'
        
        return mapped, missing
    
    def clean_string(self, value):
        """清理字符串值，将nan转换为None"""
        if pd.isna(value) or value is None or str(value).strip() == 'nan':
            return None
        return str(value).strip()
    
    def parse_integer(self, value):
        """解析整数值"""
        if pd.isna(value) or value is None:
            return None
        
        cleaned = str(value).strip()
        if cleaned == '' or cleaned.lower() == 'nan':
            return None
        
        try:
            # 尝试转换为整数
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None
    
    def parse_date(self, value):
        """解析日期"""
        if pd.isna(value) or value is None or str(value).strip() == 'nan':
            return None
        try:
            if isinstance(value, str):
                # 尝试多种日期格式
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                    try:
                        return datetime.strptime(value.strip(), fmt).date()
                    except ValueError:
                        continue
            return None
        except (ValueError, TypeError):
            return None
    
    def parse_decimal(self, value):
        """解析小数"""
        if pd.isna(value) or value is None or str(value).strip() == 'nan':
            return None
        try:
            cleaned = str(value).replace(',', '').replace('$', '').strip()
            if not cleaned:
                return None
            return Decimal(cleaned)
        except (ValueError, TypeError):
            return None
    
    def parse_percentage(self, value):
        """解析百分比"""
        if pd.isna(value) or value is None or str(value).strip() == 'nan':
            return None
        try:
            cleaned = str(value).replace('%', '').strip()
            if not cleaned:
                return None
            return Decimal(cleaned)
        except (ValueError, TypeError):
            return None
    
    def is_empty_row(self, row_values):
        """检查是否为空白行或无效行"""
        if not row_values or len(row_values) == 0:
            return True
        
        # 检查所有列是否都为空、None、'nan'或只包含空白字符
        for cell in row_values:
            if cell is not None:
                cell_str = str(cell).strip()
                if cell_str and cell_str.lower() not in ['nan', 'null', '']:
                    return False
        
        return True
    
    def is_subtotal(self, row):
        """判断是否为小计行"""
        if not row or len(row) < 3:
            return False
        
        # 方法1：检查Itin Desc列（第8列，索引7）是否包含"Sub Total"
        if len(row) > 7 and row[7]:
            if 'Sub Total' in str(row[7]):
                return True
        
        # 方法2：检查Booking Ref列（第4列，索引3）是否为空，如果为空且其他列有"Sub Total"标记，也是小计行
        booking_ref = row[3] if len(row) > 3 else None
        if (booking_ref is None or str(booking_ref).strip() == '' or str(booking_ref).strip().lower() == 'nan'):
            # Booking Ref为空，检查是否有Sub Total标记
            for i, cell in enumerate(row):
                if cell and 'Sub Total' in str(cell):
                    return True
        
        return False
    
    def import_csv_file(self, file_path):
        """导入CSV文件"""
        try:
            print(f"开始导入CSV文件: {file_path}")
            
            # 先进行CSV预处理
            df = self.preprocess_csv(file_path)
            if df is None:
                return {
                    'success': False,
                    'message': '无法读取CSV文件，请检查文件编码格式',
                    'imported_headers': 0,
                    'imported_details': 0
                }
            
            # 映射列名
            mapped_columns, missing_columns = self.map_columns(df.columns)
            print(f"列名映射结果: {mapped_columns}")
            print(f"缺少的列: {missing_columns}")
            
            if missing_columns:
                return {
                    'success': False,
                    'message': f'缺少必要的列: {", ".join(missing_columns)}',
                    'imported_headers': 0,
                    'imported_details': 0
                }
            
            # 开始导入
            imported_headers = 0
            updated_headers = 0
            imported_details = 0
            updated_details = 0
            skipped_empty_rows = 0
            skipped_invalid_refs = 0
            current_header = None
            
            for index, row in df.iterrows():
                row_data = row.to_dict()
                row_values = row.values.tolist()
                
                # 调试信息：打印前几行的内容
                if index < 5:
                    print(f"第{index}行数据: {row_values[:5]}...")
                
                # 预处理后，每行都有booking_header_id，直接提取
                booking_header_id = str(row_values[0]).strip() if row_values[0] and str(row_values[0]).strip().isdigit() else None
                
                if not booking_header_id:
                    print(f"第{index}行没有有效的booking_header_id，跳过")
                    continue
                
                # 确保有对应的头部记录
                if not current_header or current_header.booking_header_id != booking_header_id:
                    header = AthinaBookingHeader.query.filter_by(booking_header_id=booking_header_id).first()
                    if not header:
                        # 创建新的头部记录，只包含基本信息
                        # 预处理后，Corporate Name 在第二列（索引1），Book Date 在第6列（索引5）
                        corporate_name = self.clean_string(row_values[1]) if len(row_values) > 1 else None
                        book_date = self.parse_date(row_values[5]) if len(row_values) > 5 else None
                        # 创建新头部记录，只设置CSV中的字段，计算字段使用默认值
                        header = AthinaBookingHeader(
                            booking_header_id=booking_header_id,
                            corporate_name=corporate_name,
                            book_date=book_date,
                            # 计算字段使用默认值：is_all_invoiced=False, is_count_performance=False
                            # 财务汇总字段（sub_total_*）将在小计行中更新
                        )
                        db.session.add(header)
                        db.session.flush()
                        imported_headers += 1
                        print(f"创建新头部: {booking_header_id}, 公司: {header.corporate_name}")
                    else:
                        # 头部记录已存在，检查是否已核算业绩
                        if header.is_count_performance:
                            # 如果已核算业绩，检查是否有数据变更
                            corporate_name = self.clean_string(row_values[1]) if len(row_values) > 1 else None
                            
                            data_changed = False
                            changes = []
                            
                            if corporate_name and corporate_name != header.corporate_name:
                                data_changed = True
                                changes.append(f'公司名称: {header.corporate_name} -> {corporate_name}')
                            
                            if data_changed:
                                error_msg = f'错误：HID {booking_header_id} 的数据已核算业绩，不允许修改。检测到以下变更：{"; ".join(changes)}'
                                print(error_msg)
                                raise ValueError(error_msg)
                            
                            # 如果没有数据变更，继续处理但不更新头部
                            print(f"跳过已核算业绩的头部更新，HID: {booking_header_id} (数据无变更)")
                        
                        # 头部记录已存在，更新基本信息（如果新数据不为空）
                        corporate_name = self.clean_string(row_values[1]) if len(row_values) > 1 else None
                        book_date = self.parse_date(row_values[5]) if len(row_values) > 5 else None
                        
                        header_updated = False
                        
                        if corporate_name and corporate_name != header.corporate_name:
                            header.corporate_name = corporate_name
                            header_updated = True
                            print(f"更新头部公司名称: {booking_header_id}, 新公司: {corporate_name}")
                        
                        if book_date and book_date != header.book_date:
                            header.book_date = book_date
                            header_updated = True
                            print(f"更新头部预订日期: {booking_header_id}, 新日期: {book_date}")
                        
                        # 如果有任何更新，更新时间戳
                        if header_updated:
                            header.updated_at = datetime.utcnow()
                            updated_headers += 1
                            print(f"更新现有头部: {booking_header_id}, 公司: {header.corporate_name}")
                    current_header = header
                
                # 检查是否为小计行
                if self.is_subtotal(row_values):
                    print(f"发现小计行: {row_values}")
                    
                    # 如果已核算业绩，不允许更新小计数据
                    if current_header.is_count_performance:
                        # 解析新的小计数据
                        new_gross = self.parse_decimal(row_values[9]) if len(row_values) > 9 else None
                        new_cost = self.parse_decimal(row_values[13]) if len(row_values) > 13 else None
                        new_pl = self.parse_decimal(row_values[14]) if len(row_values) > 14 else None
                        new_balance = self.parse_decimal(row_values[16]) if len(row_values) > 16 else None
                        
                        # 检查是否有数据变更
                        data_changed = False
                        changes = []
                        
                        if new_gross is not None and current_header.sub_total_gross != new_gross:
                            data_changed = True
                            changes.append(f'总金额: {current_header.sub_total_gross} -> {new_gross}')
                        
                        if new_cost is not None and current_header.sub_total_cost != new_cost:
                            data_changed = True
                            changes.append(f'成本: {current_header.sub_total_cost} -> {new_cost}')
                        
                        if new_pl is not None and current_header.sub_total_pl != new_pl:
                            data_changed = True
                            changes.append(f'盈亏: {current_header.sub_total_pl} -> {new_pl}')
                        
                        if new_balance is not None and current_header.sub_total_balance != new_balance:
                            data_changed = True
                            changes.append(f'余额: {current_header.sub_total_balance} -> {new_balance}')
                        
                        if data_changed:
                            error_msg = f'错误：HID {current_header.booking_header_id} 的数据已核算业绩，不允许修改小计数据。检测到以下变更：{"; ".join(changes)}'
                            print(error_msg)
                            raise ValueError(error_msg)
                        
                        # 如果没有数据变更，跳过小计行更新
                        print(f"跳过已核算业绩的头部小计数据更新，HID: {current_header.booking_header_id} (数据无变更)")
                        continue
                    
                    # 更新头部的小计数据
                    # 预处理后的列结构：第1列=booking_header_id, 第2列=Corporate Name, 第3列=Client Name, 第4列=Booking Ref, 第5列=Book Type, 第6列=Book Date, 第7列=Dep Date, 第8列=Itin Desc, 第9列=Gross Curr, 第10列=Gross, 第11列=Gross Tax, 第12列=Disc, 第13列=Local Gross, 第14列=Local Cost, 第15列=PL, 第16列=Marg, 第17列=Balance, 第18列=Supplier, 第19列=Consultant, 第20列=Sales Consultant, 第21列=Invoice No, 第22列=Invoice Date
                    
                    subtotal_updated = False
                    
                    # 更新财务数据（总是更新，因为小计行是最新的汇总数据）
                    new_gross = self.parse_decimal(row_values[9]) if len(row_values) > 9 else None
                    new_cost = self.parse_decimal(row_values[13]) if len(row_values) > 13 else None
                    new_pl = self.parse_decimal(row_values[14]) if len(row_values) > 14 else None
                    new_balance = self.parse_decimal(row_values[16]) if len(row_values) > 16 else None
                    new_tax = self.parse_decimal(row_values[10]) if len(row_values) > 10 else None
                    new_discount = self.parse_decimal(row_values[11]) if len(row_values) > 11 else None
                    new_local_gross = self.parse_decimal(row_values[12]) if len(row_values) > 12 else None
                    new_margin = self.parse_percentage(row_values[15]) if len(row_values) > 15 else None
                    
                    # 强制更新所有小计数据（小计行总是最新的，所以直接覆盖）
                    old_balance = current_header.sub_total_balance
                    if new_gross is not None:
                        current_header.sub_total_gross = new_gross
                        subtotal_updated = True
                    if new_cost is not None:
                        current_header.sub_total_cost = new_cost
                        subtotal_updated = True
                    if new_pl is not None:
                        current_header.sub_total_pl = new_pl
                        subtotal_updated = True
                    if new_balance is not None:
                        current_header.sub_total_balance = new_balance
                        subtotal_updated = True
                        if old_balance != new_balance:
                            print(f"更新Balance: {old_balance} -> {new_balance} (booking_header_id: {current_header.booking_header_id})")
                    if new_tax is not None:
                        current_header.sub_total_tax = new_tax
                        subtotal_updated = True
                    if new_discount is not None:
                        current_header.sub_total_discount = new_discount
                        subtotal_updated = True
                    if new_local_gross is not None:
                        current_header.sub_total_local_gross = new_local_gross
                        subtotal_updated = True
                    if new_margin is not None:
                        current_header.sub_total_margin = new_margin
                        subtotal_updated = True
                    
                    # 更新顾问和发票信息（如果存在且为空）
                    if not current_header.consultant:
                        consultant = self.clean_string(row_values[18]) if len(row_values) > 18 else None
                        if consultant:
                            current_header.consultant = consultant
                            subtotal_updated = True
                    if not current_header.sales_consultant:
                        sales_consultant = self.clean_string(row_values[19]) if len(row_values) > 19 else None
                        if sales_consultant:
                            current_header.sales_consultant = sales_consultant
                            subtotal_updated = True
                    # invoice_no 和 invoice_date 已从 header 中移除，改为从 detail 中获取
                    
                    # 如果有任何更新，更新时间戳
                    if subtotal_updated:
                        current_header.updated_at = datetime.utcnow()
                        updated_headers += 1
                        print(f"更新头部小计数据: Gross={current_header.sub_total_gross}, Cost={current_header.sub_total_cost}, PL={current_header.sub_total_pl}, Balance={current_header.sub_total_balance}")
                    
                    # Sub Total行不应该被录入到athina_booking_details表中，只更新header的汇总数据
                    # 跳过创建detail记录，继续处理下一行
                    continue
                
                # 普通明细行
                else:
                    # 检查是否为空白行或无效行
                    if self.is_empty_row(row_values):
                        print(f"第{index}行是空白行，跳过")
                        skipped_empty_rows += 1
                        continue
                    
                    # 首先检查booking_ref是否有效（这是必需的）
                    booking_ref = self.parse_integer(row_values[3]) if len(row_values) > 3 else None
                    
                    # 如果booking_ref为空或无效，跳过此记录
                    # 注意：Sub Total行的booking_ref应该是空的，但应该在小计行检查时已经处理了
                    if booking_ref is None:
                        print(f"第{index}行booking_ref为空或无效，跳过")
                        skipped_invalid_refs += 1
                        continue
                    
                    # 注意：不再跳过Gross为0的记录，因为有些记录Gross可能为0但仍然有效（如ref 940）
                    
                    # 检查是否包含有效业务数据
                    has_client_name = any(cell and str(cell).strip() and str(cell).strip() != 'nan' 
                                        for cell in row_values[2:4])
                    has_other_data = any(cell and str(cell).strip() and str(cell).strip() != 'nan' 
                                       for cell in row_values[4:8])  # 检查其他业务字段
                    
                    if has_client_name or has_other_data:
                        
                        # 基于booking_ref查找现有记录
                        existing_detail = AthinaBookingDetail.query.filter_by(booking_ref=booking_ref).first()
                        
                        if existing_detail:
                            # 检查是否已核算业绩，如果已核算则不允许修改ref和hid相关数据
                            header_for_detail = existing_detail.header
                            if header_for_detail and header_for_detail.is_count_performance:
                                # 检查是否有数据变更（关键字段：booking_ref, header_id/booking_header_id, 财务数据）
                                new_gross_amount = self.parse_decimal(row_values[9]) if len(row_values) > 9 else None
                                new_local_cost = self.parse_decimal(row_values[13]) if len(row_values) > 13 else None
                                new_profit_loss = self.parse_decimal(row_values[14]) if len(row_values) > 14 else None
                                new_balance = self.parse_decimal(row_values[16]) if len(row_values) > 16 else None
                                
                                # 检查booking_ref是否变化
                                if existing_detail.booking_ref != booking_ref:
                                    error_msg = f'错误：预订参考号 {existing_detail.booking_ref} 的数据已核算业绩，不允许修改。尝试修改为 {booking_ref} 的操作被拒绝。'
                                    print(error_msg)
                                    raise ValueError(error_msg)
                                
                                # 检查header_id/HID是否变化
                                if existing_detail.header_id != current_header.id:
                                    error_msg = f'错误：预订参考号 {booking_ref} (HID: {header_for_detail.booking_header_id}) 的数据已核算业绩，不允许修改HID。尝试修改为 HID {current_header.booking_header_id} 的操作被拒绝。'
                                    print(error_msg)
                                    raise ValueError(error_msg)
                                
                                # 检查关键财务数据是否有变化
                                data_changed = False
                                changes = []
                                
                                if new_gross_amount is not None and existing_detail.gross_amount != new_gross_amount:
                                    data_changed = True
                                    changes.append(f'总金额: {existing_detail.gross_amount} -> {new_gross_amount}')
                                
                                if new_local_cost is not None and existing_detail.local_cost != new_local_cost:
                                    data_changed = True
                                    changes.append(f'成本: {existing_detail.local_cost} -> {new_local_cost}')
                                
                                if new_profit_loss is not None and existing_detail.profit_loss != new_profit_loss:
                                    data_changed = True
                                    changes.append(f'盈亏: {existing_detail.profit_loss} -> {new_profit_loss}')
                                
                                if new_balance is not None and existing_detail.balance != new_balance:
                                    data_changed = True
                                    changes.append(f'余额: {existing_detail.balance} -> {new_balance}')
                                
                                if data_changed:
                                    error_msg = f'错误：预订参考号 {booking_ref} (HID: {header_for_detail.booking_header_id}) 的数据已核算业绩，不允许修改。检测到以下变更：{"; ".join(changes)}'
                                    print(error_msg)
                                    raise ValueError(error_msg)
                                
                                # 如果没有数据变更，跳过此记录的更新
                                print(f"跳过已核算业绩的记录，booking_ref: {booking_ref}, HID: {header_for_detail.booking_header_id} (数据无变更)")
                                continue
                            
                            # 更新现有明细记录（以最新导入的数据为准，强制更新所有字段）
                            print(f"更新现有明细记录，booking_ref: {booking_ref}")
                            
                            # 解析所有字段值
                            new_corporate_name = self.clean_string(row_values[1]) if len(row_values) > 1 else None
                            new_client_name = self.clean_string(row_values[2]) if len(row_values) > 2 else None
                            new_book_type = self.clean_string(row_values[4]) if len(row_values) > 4 else None
                            new_book_date = self.parse_date(row_values[5]) if len(row_values) > 5 else None
                            new_dep_date = self.parse_date(row_values[6]) if len(row_values) > 6 else None
                            new_itin_desc = self.clean_string(row_values[7]) if len(row_values) > 7 else None
                            new_gross_curr = self.clean_string(row_values[8]) if len(row_values) > 8 else None
                            new_gross_amount = self.parse_decimal(row_values[9]) if len(row_values) > 9 else None
                            new_gross_tax = self.parse_decimal(row_values[10]) if len(row_values) > 10 else None
                            new_discount = self.parse_decimal(row_values[11]) if len(row_values) > 11 else None
                            new_local_gross = self.parse_decimal(row_values[12]) if len(row_values) > 12 else None
                            new_local_cost = self.parse_decimal(row_values[13]) if len(row_values) > 13 else None
                            new_profit_loss = self.parse_decimal(row_values[14]) if len(row_values) > 14 else None
                            new_margin = self.parse_percentage(row_values[15]) if len(row_values) > 15 else None
                            new_balance = self.parse_decimal(row_values[16]) if len(row_values) > 16 else None
                            new_supplier = self.clean_string(row_values[17]) if len(row_values) > 17 else None
                            new_consultant = self.clean_string(row_values[18]) if len(row_values) > 18 else None
                            new_sales_consultant = self.clean_string(row_values[19]) if len(row_values) > 19 else None
                            new_invoice_no = self.clean_string(row_values[20]) if len(row_values) > 20 else None
                            new_invoice_date = self.parse_date(row_values[21]) if len(row_values) > 21 else None
                            
                            # 强制更新所有字段（以最新导入的数据为准）
                            existing_detail.corporate_name = new_corporate_name
                            existing_detail.client_name = new_client_name
                            existing_detail.book_type = new_book_type
                            existing_detail.book_date = new_book_date
                            existing_detail.dep_date = new_dep_date
                            existing_detail.itin_desc = new_itin_desc
                            existing_detail.gross_curr = new_gross_curr
                            existing_detail.gross_amount = new_gross_amount
                            existing_detail.gross_tax = new_gross_tax
                            existing_detail.discount = new_discount
                            existing_detail.local_gross = new_local_gross
                            existing_detail.local_cost = new_local_cost
                            existing_detail.profit_loss = new_profit_loss
                            existing_detail.margin = new_margin
                            existing_detail.balance = new_balance
                            existing_detail.supplier = new_supplier
                            existing_detail.consultant = new_consultant
                            existing_detail.sales_consultant = new_sales_consultant
                            existing_detail.invoice_no = new_invoice_no
                            existing_detail.invoice_date = new_invoice_date
                            
                            # 确保header_id正确（如果booking_ref对应的detail现在属于不同的header）
                            existing_detail.header_id = current_header.id
                            
                            # 更新对应header的开票状态
                            if existing_detail.header:
                                existing_detail.header.update_invoice_status()
                            
                            # 更新时间戳
                            existing_detail.updated_at = datetime.utcnow()
                            updated_details += 1
                            print(f"更新明细记录，booking_ref: {booking_ref}, 客户: {new_client_name or existing_detail.client_name}")
                        else:
                            # 创建新的明细记录
                            # 预处理后的列结构：第1列=booking_header_id, 第2列=Corporate Name, 第3列=Client Name, 第4列=Booking Ref, 第5列=Book Type, 第6列=Book Date, 第7列=Dep Date, 第8列=Itin Desc, 第9列=Gross Curr, 第10列=Gross, 第11列=Gross Tax, 第12列=Disc, 第13列=Local Gross, 第14列=Local Cost, 第15列=PL, 第16列=Marg, 第17列=Balance, 第18列=Supplier, 第19列=Consultant, 第20列=Sales Consultant, 第21列=Invoice No, 第22列=Invoice Date
                            detail = AthinaBookingDetail(
                                header_id=current_header.id,
                                # 业务信息
                                corporate_name=self.clean_string(row_values[1]) if len(row_values) > 1 else None,  # Corporate Name
                                client_name=self.clean_string(row_values[2]) if len(row_values) > 2 else None,  # Client Name
                                booking_ref=self.parse_integer(row_values[3]) if len(row_values) > 3 else None,  # Booking Ref
                                book_type=self.clean_string(row_values[4]) if len(row_values) > 4 else None,  # Book Type
                                book_date=self.parse_date(row_values[5]) if len(row_values) > 5 else None,  # Book Date
                                dep_date=self.parse_date(row_values[6]) if len(row_values) > 6 else None,  # Dep Date
                                itin_desc=self.clean_string(row_values[7]) if len(row_values) > 7 else None,  # Itin Desc
                                # 财务信息
                                gross_curr=self.clean_string(row_values[8]) if len(row_values) > 8 else None,  # Gross Curr
                                gross_amount=self.parse_decimal(row_values[9]) if len(row_values) > 9 else None,  # Gross
                                gross_tax=self.parse_decimal(row_values[10]) if len(row_values) > 10 else None,  # Gross Tax
                                discount=self.parse_decimal(row_values[11]) if len(row_values) > 11 else None,  # Disc
                                local_gross=self.parse_decimal(row_values[12]) if len(row_values) > 12 else None,  # Local Gross
                                local_cost=self.parse_decimal(row_values[13]) if len(row_values) > 13 else None,  # Local Cost
                                profit_loss=self.parse_decimal(row_values[14]) if len(row_values) > 14 else None,  # PL
                                margin=self.parse_percentage(row_values[15]) if len(row_values) > 15 else None,  # Marg
                                balance=self.parse_decimal(row_values[16]) if len(row_values) > 16 else None,  # Balance
                                # 供应商信息
                                supplier=self.clean_string(row_values[17]) if len(row_values) > 17 else None,  # Supplier
                                consultant=self.clean_string(row_values[18]) if len(row_values) > 18 else None,  # Consultant
                                sales_consultant=self.clean_string(row_values[19]) if len(row_values) > 19 else None,  # Sales Consultant
                                # 发票信息
                                invoice_no=self.clean_string(row_values[20]) if len(row_values) > 20 else None,  # Invoice No
                                invoice_date=self.parse_date(row_values[21]) if len(row_values) > 21 else None,  # Invoice Date
                                # 特殊标记
                                is_subtotal=False
                            )
                            db.session.add(detail)
                            imported_details += 1
                            # 更新对应header的开票状态
                            current_header.update_invoice_status()
                            print(f"创建新明细记录，header_id: {current_header.id}, booking_ref: {booking_ref}, 客户: {detail.client_name}")
                        
                        # 同时更新头部的顾问信息（如果头部还没有这些信息）
                        # 注意：只更新CSV字段，不覆盖计算字段（is_all_invoiced, is_count_performance）
                        detail_to_check = existing_detail if existing_detail else detail
                        if not current_header.consultant and detail_to_check.consultant:
                            current_header.consultant = detail_to_check.consultant
                        if not current_header.sales_consultant and detail_to_check.sales_consultant:
                            current_header.sales_consultant = detail_to_check.sales_consultant
                        # invoice_no 和 invoice_date 已从 header 中移除，改为从 detail 中获取
                        # is_all_invoiced 和 is_count_performance 是计算字段，不在这里更新
                    else:
                        print(f"第{index}行不包含有效业务数据，跳过")
            
            # 更新所有header的is_all_invoiced状态（计算字段）
            all_headers = AthinaBookingHeader.query.all()
            for h in all_headers:
                h.update_invoice_status()
            
            # 提交所有更改
            db.session.commit()
            print(f"导入完成！新增 {imported_headers} 个预订头部，{imported_details} 个明细记录；更新 {updated_headers} 个预订头部，{updated_details} 个明细记录；跳过 {skipped_empty_rows} 个空白行，{skipped_invalid_refs} 个无效引用")
            
            return {
                'success': True,
                'message': f'导入完成！新增 {imported_headers} 个预订头部，{imported_details} 个明细记录；更新 {updated_headers} 个预订头部，{updated_details} 个明细记录；跳过 {skipped_empty_rows} 个空白行，{skipped_invalid_refs} 个无效引用',
                'imported_headers': imported_headers,
                'updated_headers': updated_headers,
                'imported_details': imported_details,
                'updated_details': updated_details,
                'skipped_empty_rows': skipped_empty_rows,
                'skipped_invalid_refs': skipped_invalid_refs,
                'total_headers': imported_headers + updated_headers,
                'total_details': imported_details + updated_details,
                'total_processed': imported_headers + updated_headers + imported_details + updated_details + skipped_empty_rows + skipped_invalid_refs
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"导入过程中发生错误: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'导入失败: {str(e)}',
                'error_details': traceback.format_exc(),
                'imported_headers': 0,
                'imported_details': 0
            }
    
    def get_booking_headers(self, page=1, per_page=20, search=None):
        """获取预订头部列表"""
        query = AthinaBookingHeader.query
        
        if search:
            query = query.filter(
                AthinaBookingHeader.booking_header_id.contains(search) |
                AthinaBookingHeader.corporate_name.contains(search)
            )
        
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'headers': [{
                'id': header.id,
                'booking_header_id': header.booking_header_id,
                'corporate_name': header.corporate_name,
                'book_date': header.book_date.isoformat() if header.book_date else None,
                'sub_total_gross': float(header.sub_total_gross) if header.sub_total_gross else 0,
                'sub_total_cost': float(header.sub_total_cost) if header.sub_total_cost else 0,
                'sub_total_pl': float(header.sub_total_pl) if header.sub_total_pl else 0,
                'sub_total_balance': float(header.sub_total_balance) if header.sub_total_balance else 0,
                'consultant': header.consultant,
                'sales_consultant': header.sales_consultant,
                'invoice_no': header.invoice_no,
                'invoice_date': header.invoice_date.isoformat() if header.invoice_date else None,
                'created_at': header.created_at.isoformat() if header.created_at else None
            } for header in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }
    
    def get_booking_details(self, header_id, page=1, per_page=20):
        """获取预订明细列表"""
        query = AthinaBookingDetail.query.filter_by(header_id=header_id)
        
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'details': [{
                'id': detail.id,
                'corporate_name': detail.corporate_name,
                'client_name': detail.client_name,
                'booking_ref': detail.booking_ref,
                'book_type': detail.book_type,
                'book_date': detail.book_date.isoformat() if detail.book_date else None,
                'dep_date': detail.dep_date.isoformat() if detail.dep_date else None,
                'itin_desc': detail.itin_desc,
                'gross_amount': float(detail.gross_amount) if detail.gross_amount else 0,
                'gross_tax': float(detail.gross_tax) if detail.gross_tax else 0,
                'discount': float(detail.discount) if detail.discount else 0,
                'local_gross': float(detail.local_gross) if detail.local_gross else 0,
                'local_cost': float(detail.local_cost) if detail.local_cost else 0,
                'profit_loss': float(detail.profit_loss) if detail.profit_loss else 0,
                'margin': float(detail.margin) if detail.margin else 0,
                'balance': float(detail.balance) if detail.balance else 0,
                'supplier': detail.supplier,
                'consultant': detail.consultant,
                'sales_consultant': detail.sales_consultant,
                'invoice_no': detail.invoice_no,
                'invoice_date': detail.invoice_date.isoformat() if detail.invoice_date else None,
                'is_subtotal': detail.is_subtotal,
                'created_at': detail.created_at.isoformat() if detail.created_at else None
            } for detail in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }
    
    def get_import_stats(self):
        """获取导入统计信息"""
        try:
            header_count = AthinaBookingHeader.query.count()
            detail_count = AthinaBookingDetail.query.count()
            
            # 获取最近更新的记录数量
            from datetime import datetime, timedelta
            recent_threshold = datetime.utcnow() - timedelta(days=7)
            
            recent_headers = AthinaBookingHeader.query.filter(
                AthinaBookingHeader.updated_at >= recent_threshold
            ).count()
            
            recent_details = AthinaBookingDetail.query.filter(
                AthinaBookingDetail.updated_at >= recent_threshold
            ).count()
            
            return {
                'success': True,
                'header_count': header_count,
                'detail_count': detail_count,
                'recent_headers': recent_headers,
                'recent_details': recent_details,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取统计信息失败: {str(e)}'
            }
    
    def update_booking_data(self, booking_header_id, field_updates):
        """专门用于更新特定预订数据的方法"""
        try:
            header = AthinaBookingHeader.query.filter_by(booking_header_id=booking_header_id).first()
            if not header:
                return {
                    'success': False,
                    'message': f'未找到预订头部记录: {booking_header_id}'
                }
            
            updated_fields = []
            
            # 更新头部记录
            for field, value in field_updates.items():
                if hasattr(header, field):
                    old_value = getattr(header, field)
                    if old_value != value:
                        setattr(header, field, value)
                        updated_fields.append(field)
            
            # 如果有更新，更新时间戳
            if updated_fields:
                header.updated_at = datetime.utcnow()
                db.session.commit()
                
                return {
                    'success': True,
                    'message': f'成功更新预订 {booking_header_id} 的字段: {", ".join(updated_fields)}',
                    'updated_fields': updated_fields,
                    'updated_at': header.updated_at.isoformat()
                }
            else:
                return {
                    'success': True,
                    'message': '没有字段需要更新',
                    'updated_fields': []
                }
                
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'更新失败: {str(e)}'
            }
