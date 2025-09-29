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
                df.iloc[:, 0] = df.iloc[:, 0].fillna(method='ffill')
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
    
    def is_subtotal(self, row):
        """判断是否为小计行"""
        if not row or len(row) < 3:
            return False
        
        # 检查Itin Desc列是否包含"Sub Total"
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
            imported_details = 0
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
                        header = AthinaBookingHeader(
                            booking_header_id=booking_header_id,
                            corporate_name=corporate_name,
                            book_date=book_date
                        )
                        db.session.add(header)
                        db.session.flush()
                        imported_headers += 1
                        print(f"创建新头部: {booking_header_id}, 公司: {header.corporate_name}")
                    current_header = header
                
                # 检查是否为小计行
                if self.is_subtotal(row_values):
                    print(f"发现小计行: {row_values}")
                    # 更新头部的小计数据
                    # 预处理后的列结构：第1列=booking_header_id, 第2列=Corporate Name, 第3列=Client Name, 第4列=Booking Ref, 第5列=Book Type, 第6列=Book Date, 第7列=Dep Date, 第8列=Itin Desc, 第9列=Gross Curr, 第10列=Gross, 第11列=Gross Tax, 第12列=Disc, 第13列=Local Gross, 第14列=Local Cost, 第15列=PL, 第16列=Marg, 第17列=Balance, 第18列=Supplier, 第19列=Consultant, 第20列=Sales Consultant, 第21列=Invoice No, 第22列=Invoice Date
                    current_header.sub_total_gross = self.parse_decimal(row_values[9]) if len(row_values) > 9 else None  # Gross
                    current_header.sub_total_cost = self.parse_decimal(row_values[13]) if len(row_values) > 13 else None  # Local Cost
                    current_header.sub_total_pl = self.parse_decimal(row_values[14]) if len(row_values) > 14 else None  # PL
                    current_header.sub_total_balance = self.parse_decimal(row_values[16]) if len(row_values) > 16 else None  # Balance
                    current_header.sub_total_tax = self.parse_decimal(row_values[10]) if len(row_values) > 10 else None  # Gross Tax
                    current_header.sub_total_discount = self.parse_decimal(row_values[11]) if len(row_values) > 11 else None  # Disc
                    current_header.sub_total_local_gross = self.parse_decimal(row_values[12]) if len(row_values) > 12 else None  # Local Gross
                    current_header.sub_total_margin = self.parse_percentage(row_values[15]) if len(row_values) > 15 else None  # Marg
                    
                    # 同时更新头部的顾问和发票信息（如果存在）
                    if not current_header.consultant:
                        current_header.consultant = self.clean_string(row_values[18]) if len(row_values) > 18 else None  # Consultant
                    if not current_header.sales_consultant:
                        current_header.sales_consultant = self.clean_string(row_values[19]) if len(row_values) > 19 else None  # Sales Consultant
                    if not current_header.invoice_no:
                        current_header.invoice_no = self.clean_string(row_values[20]) if len(row_values) > 20 else None  # Invoice No
                    if not current_header.invoice_date:
                        current_header.invoice_date = self.parse_date(row_values[21]) if len(row_values) > 21 else None  # Invoice Date
                    
                    # 创建小计明细记录
                    detail = AthinaBookingDetail(
                        header_id=current_header.id,
                        is_subtotal=True,
                        gross_amount=current_header.sub_total_gross,
                        gross_tax=current_header.sub_total_tax,
                        discount=current_header.sub_total_discount,
                        local_gross=current_header.sub_total_local_gross,
                        local_cost=current_header.sub_total_cost,
                        profit_loss=current_header.sub_total_pl,
                        margin=current_header.sub_total_margin,
                        balance=current_header.sub_total_balance
                    )
                    db.session.add(detail)
                    imported_details += 1
                    print(f"更新头部小计数据: Gross={current_header.sub_total_gross}, Cost={current_header.sub_total_cost}, PL={current_header.sub_total_pl}")
                
                # 普通明细行
                else:
                    # 检查是否包含有效业务数据
                    has_client_name = any(cell and str(cell).strip() and str(cell).strip() != 'nan' 
                                        for cell in row_values[2:4])
                    has_booking_ref = any(cell and str(cell).strip() and str(cell).strip() != 'nan' 
                                        for cell in row_values[3:5])
                    
                    if has_client_name or has_booking_ref:
                        # 创建明细记录，包含所有业务和财务数据
                        # 预处理后的列结构：第1列=booking_header_id, 第2列=Corporate Name, 第3列=Client Name, 第4列=Booking Ref, 第5列=Book Type, 第6列=Book Date, 第7列=Dep Date, 第8列=Itin Desc, 第9列=Gross Curr, 第10列=Gross, 第11列=Gross Tax, 第12列=Disc, 第13列=Local Gross, 第14列=Local Cost, 第15列=PL, 第16列=Marg, 第17列=Balance, 第18列=Supplier, 第19列=Consultant, 第20列=Sales Consultant, 第21列=Invoice No, 第22列=Invoice Date
                        detail = AthinaBookingDetail(
                            header_id=current_header.id,
                            # 业务信息
                            corporate_name=self.clean_string(row_values[1]) if len(row_values) > 1 else None,  # Corporate Name
                            client_name=self.clean_string(row_values[2]) if len(row_values) > 2 else None,  # Client Name
                            booking_ref=self.clean_string(row_values[3]) if len(row_values) > 3 else None,  # Booking Ref
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
                        print(f"创建明细记录，header_id: {current_header.id}, 客户: {detail.client_name}")
                        
                        # 同时更新头部的顾问和发票信息（如果头部还没有这些信息）
                        if not current_header.consultant and detail.consultant:
                            current_header.consultant = detail.consultant
                        if not current_header.sales_consultant and detail.sales_consultant:
                            current_header.sales_consultant = detail.sales_consultant
                        if not current_header.invoice_no and detail.invoice_no:
                            current_header.invoice_no = detail.invoice_no
                        if not current_header.invoice_date and detail.invoice_date:
                            current_header.invoice_date = detail.invoice_date
                    else:
                        print(f"第{index}行不包含有效业务数据，跳过")
            
            # 提交所有更改
            db.session.commit()
            print(f"导入成功！共导入 {imported_headers} 个预订头部，{imported_details} 个明细记录")
            
            return {
                'success': True,
                'message': f'导入成功！共导入 {imported_headers} 个预订头部，{imported_details} 个明细记录',
                'imported_headers': imported_headers,
                'imported_details': imported_details
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
            
            return {
                'success': True,
                'header_count': header_count,
                'detail_count': detail_count
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取统计信息失败: {str(e)}'
            }
