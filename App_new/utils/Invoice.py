import pandas as pd
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from App_new.utils.report_utils import get_report_headers

# 设置pandas显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# 配置日志
logger = logging.getLogger(__name__)
# 确保日志处理器使用UTF-8编码
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
handler.encoding = 'utf-8'
logger.addHandler(handler)


class CountHid:
    """
    处理HID和Invoice数据的统计类
    用于计算未结算业绩和利润分析
    """

    def __init__(self, booking_path: str, name: str = "Zz"):
        """
        初始化CountHid类

        Args:
            booking_path: 账单数据根路径
            name: 子文件夹名称，默认为"Zz"
        """
        self._path = Path(booking_path) / name
        self._invoice_path = self._path / "Invoice"
        self._hid_path = self._path / "HID"
        self._complete_file = self._path / "complete.txt"
        self._disputed_file = self._path / "disputed.txt"

        # 获取表头配置
        self.invoice_headers = get_report_headers('invoice_data')
        self.hid_headers = get_report_headers('order_report')  # 改为使用 order_report

        # 验证路径
        self._validate_paths()

    def _validate_paths(self):
        """验证必要的文件夹路径是否存在"""
        if not self._path.exists():
            raise FileNotFoundError(f"路径不存在: {self._path}")

        if not self._invoice_path.exists():
            logger.warning(f"Invoice文件夹不存在: {self._invoice_path}")

        if not self._hid_path.exists():
            logger.warning(f"HID文件夹不存在: {self._hid_path}")

    def _read_excel_file(self, file_path: Path, sheet_name: str = 'Sheet1') -> pd.DataFrame:
        """
        安全读取Excel文件

        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称

        Returns:
            DataFrame: 读取的数据
        """
        try:
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return pd.DataFrame()

            # 读取Excel时禁用日期自动解析，将所有数据作为字符串读取
            # 使用 converters 将所有列转换为字符串
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            # 立即将所有列转换为字符串，避免自动日期解析
            df = df.astype(str)
            return df
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return pd.DataFrame()

    def _process_invoice_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理Invoice数据，应用列映射和清理
        """
        if df.empty:
            return df

        try:
            # 应用表头
            if len(df.columns) == len(self.invoice_headers):
                df.columns = self.invoice_headers
            else:
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
            
            # 删除关键列的空值行
            df = df.dropna(subset=['hid', 'inv', 'company_name'])
            if df.empty:
                return df

            # 整数字列转换（先转float再转int，避免字符串'162712.0'的错误）
            numeric_cols = ['hid', 'inv', 'company_name']
            for col in numeric_cols:
                df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            # 浮点数字列转换（根据新的invoice_data表头）
            numeric_cols = ['gross', 'commission', 'discount', 'selling_price', 'cost_price', 'profit', 
                          'profit_margin', 'balance', 'pax_count', 'invoice_profit']

            for col in numeric_cols:
                if col in df.columns:
                    df.loc[:, col] = pd.to_numeric(df.loc[:, col], errors='coerce').fillna(0)

            # 字符串列转换（根据新的invoice_data表头）
            str_cols = ['company_name', 'client_name', 'itinerary', 'currency', 'invoice_person',
                       'contact_person', 'salesperson', 'remarks', 'sales_account', 
                       'invoice_account', 'remarks_1', 'remarks_2', 'remarks_3']

            for col in str_cols:
                if col in df.columns:
                    # 使用更安全的方式转换字符串
                    df.loc[:, col] = df.loc[:, col].fillna('').astype(str)
            
            # 过滤掉汇总行（如"Grand Total"等）
            if 'client_name' in df.columns:
                filter_keywords = ['total', 'Total', 'TOTAL', '合计', '小计', 'Grand Total']
                for keyword in filter_keywords:
                    df = df[~df['client_name'].astype(str).str.contains(keyword, na=False, case=False)]
            
            if df.empty:
                logger.warning("过滤汇总行后Invoice数据为空")
                return pd.DataFrame()

            # 处理日期列 - 使用与HID相同的日期解析逻辑
            # 注意：Excel中的日期格式是错位的，需要特殊处理
            # 显示为 YYYY/MM/DD 但实际是 DD/MM/YY
            # 例如：2003/9/25 实际是 03/SEP/25 (2025-09-03)
            date_cols = ['inv_date', 'order_date', 'travel_date', 'created_date', 'dep_date', 'hdid_date', 
                        'departure_date', 'itinerary_date', 'hid_date']
            
            for col in date_cols:
                if col in df.columns:
                    # 定义日期转换函数（与HID相同的逻辑）
                    def parse_date(date_str):
                        try:
                            if pd.isna(date_str) or date_str == 'nan' or date_str == '':
                                return pd.NaT
                            
                            date_str = str(date_str).strip()
                            
                            # 处理已被Pandas解析的日期格式 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
                            if '-' in date_str:
                                # 提取日期部分（去掉可能的时间部分）
                                date_part = date_str.split(' ')[0] if ' ' in date_str else date_str
                                parts = date_part.split('-')
                                
                                if len(parts) == 3:
                                    # Pandas解析的格式：YYYY-MM-DD
                                    # 实际Excel含义：DD-MM-YY（位置错位）
                                    # 例如："2001-11-24" 实际是 日=01, 月=11, 年=24
                                    year_part = parts[0]     # Pandas当作"年"，实际是"日"
                                    month = int(parts[1])    # 月份（正确）
                                    day_part = parts[2]      # Pandas当作"日"，实际是"年"
                                    
                                    # 判断：如果year_part是4位数字(>999)，说明这是错位格式，需要转换
                                    if int(year_part) > 999:
                                        # 错位格式：YYYY-MM-DD → DD-MM-YY
                                        # 例如："2001-11-24" → 日=01, 月=11, 年=24
                                        day = int(year_part[-2:])  # 取后两位作为日（2001 → 01）
                                        year_suffix = int(day_part)  # 取最后一部分作为年（24 → 24）
                                    elif int(year_part) > 31:
                                        # 可能是正常的年份格式，直接返回
                                        return pd.to_datetime(date_part, format='%Y-%m-%d', errors='coerce')
                                    else:
                                        # 正常的DD-MM-YY格式
                                        day = int(year_part)
                                        year_suffix = int(day_part)
                                    
                                    # 转换为四位年份
                                    if year_suffix >= 20:
                                        year = 2000 + year_suffix
                                    else:
                                        year = 2000 + year_suffix
                                    
                                    return pd.Timestamp(year=year, month=month, day=day)
                            
                            # 尝试分割日期字符串（原始格式 DD/MM/YY）
                            parts = str(date_str).split('/')
                            if len(parts) == 3:
                                part1 = int(parts[0])
                                part2 = int(parts[1])
                                part3 = int(parts[2])
                                
                                # 如果part1 > 31，说明这是标准日期格式
                                if part1 > 31:
                                    return pd.to_datetime(date_str, format='%Y/%m/%d', errors='coerce')
                                else:
                                    # 这是错位格式：DD/MM/YY
                                    day = part1
                                    month = part2
                                    year_suffix = part3
                                    
                                    # 将两位年份转换为四位
                                    if year_suffix >= 20:
                                        year = 2000 + year_suffix
                                    else:
                                        year = 2000 + year_suffix
                                    
                                    return pd.Timestamp(year=year, month=month, day=day)
                            else:
                                return pd.to_datetime(date_str, errors='coerce')
                        except Exception as e:
                            return pd.NaT
                    
                    # 应用日期转换（避免SettingWithCopyWarning）
                    df = df.copy()
                    df[col] = df[col].apply(parse_date)

            return df

        except Exception as e:
            logger.error(f"处理Invoice数据失败: {e}")
            return pd.DataFrame()

    def _process_hid_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理HID数据，应用列映射和清理
        """
        if df.empty:
            return df

        try:
            # 应用表头
            if len(df.columns) == len(self.hid_headers):
                df.columns = self.hid_headers
            else:
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
            
            # 检查 'hid' 列是否存在
            if 'hid' in df.columns:
                df = df.dropna(subset=['hid'])
            else:
                logger.warning("HID数据中没有找到 'hid' 列，可用的列: " + str(list(df.columns)))
                # 如果没有 'hid' 列，尝试使用第一列作为 hid
                if len(df.columns) > 0:
                    df.columns.values[0] = 'hid'
                    df = df.dropna(subset=['hid'])
                else:
                    logger.error("HID数据为空或没有列")
                    return pd.DataFrame()

            if df.empty:
                return df
            # 数字列转换
            numeric_cols = ['hid', 'selling_price', 'cost_price', 'profit', 'profit_margin', 'balance', 'pax_count']
            for col in numeric_cols:
                if col in df.columns:
                    df.loc[:, col] = pd.to_numeric(df.loc[:, col], errors='coerce').fillna(0)

            # 字符串列转换（使用新的列名）
            str_cols = ['company_name', 'passenger_name', 'employee_name', 'salesperson_name', 'itinerary', 'currency', 'remarks']
            for col in str_cols:
                if col in df.columns:
                    # 使用更安全的方式转换字符串
                    df.loc[:, col] = df.loc[:, col].fillna('').astype(str)
            
            # 删除 company_name 为空的行（包括 nan 和空字符串）
            df = df[df['company_name'].str.strip() != '']
            df = df[df['company_name'] != 'nan']
            
            # 过滤掉汇总行（如"Grand Total"等）
            summary_columns = ['company_name', 'passenger_name', 'itinerary']
            filter_keywords = ['total', 'Total', 'TOTAL', '合计', '小计', 'Grand Total', 'Grand Tot']
            
            for col in summary_columns:
                if col in df.columns:
                    for keyword in filter_keywords:
                        mask = df[col].str.contains(keyword, na=False, case=False)
                        if mask.any():
                            df = df[~mask]
            
            if df.empty:
                logger.warning("过滤汇总行后数据为空")
                return pd.DataFrame()

            # 例如：2003/9/25 实际是 03/SEP/25 (2025-09-03)
            date_cols = ['booking_date', 'departure_date']

            for col in date_cols:
                if col in df.columns:
                    # 定义日期转换函数
                    def parse_date(date_str):
                        try:
                            if pd.isna(date_str) or date_str == 'nan' or date_str == '':
                                return pd.NaT
                            
                            date_str = str(date_str).strip()
                            
                            # 处理已被Pandas解析的日期格式 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
                            if '-' in date_str:
                                # 提取日期部分（去掉可能的时间部分）
                                date_part = date_str.split(' ')[0] if ' ' in date_str else date_str
                                parts = date_part.split('-')
                                
                                if len(parts) == 3:
                                    # Pandas解析的格式：YYYY-MM-DD
                                    # 实际Excel含义：DD-MM-YY（位置错位）
                                    # 例如："2001-11-24" 实际是 日=01, 月=11, 年=24
                                    year_part = parts[0]     # Pandas当作"年"，实际是"日"
                                    month = int(parts[1])    # 月份（正确）
                                    day_part = parts[2]      # Pandas当作"日"，实际是"年"
                                    
                                    # 判断：如果year_part是4位数字(>999)，说明这是错位格式，需要转换
                                    if int(year_part) > 999:
                                        # 错位格式：YYYY-MM-DD → DD-MM-YY
                                        # 例如："2001-11-24" → 日=01, 月=11, 年=24
                                        day = int(year_part[-2:])  # 取后两位作为日（2001 → 01）
                                        year_suffix = int(day_part)  # 取最后一部分作为年（24 → 24）
                                    elif int(year_part) > 31:
                                        # 可能是正常的年份格式，直接返回
                                        return pd.to_datetime(date_part, format='%Y-%m-%d', errors='coerce')
                                    else:
                                        # 正常的DD-MM-YY格式
                                        day = int(year_part)
                                        year_suffix = int(day_part)
                                    
                                    # 转换为四位年份
                                    if year_suffix >= 20:
                                        year = 2000 + year_suffix
                                    else:
                                        year = 2000 + year_suffix
                                    
                                    return pd.Timestamp(year=year, month=month, day=day)
                            
                            # 尝试分割日期字符串（原始格式 DD/MM/YY）
                            parts = str(date_str).split('/')
                            if len(parts) == 3:
                                # 格式：YYYY/MM/DD 或 DD/MM/YY，实际含义：DD/MM/YY
                                part1 = int(parts[0])    # 可能是日(1-31)或错误的年(>100)
                                part2 = int(parts[1])    # 月
                                part3 = int(parts[2])    # 可能是年(20-99)或日(1-31)
                                
                                # 判断：如果part1 > 31，说明这是标准日期格式，直接解析
                                if part1 > 31:
                                    # 这是标准格式 YYYY/MM/DD，直接解析
                                    return pd.to_datetime(date_str, format='%Y/%m/%d', errors='coerce')
                                else:
                                    # 这是错位格式：DD/MM/YY
                                    day = part1
                                    month = part2
                                    year_suffix = part3
                                    
                                    # 将两位年份转换为四位
                                    # 20-99 → 2020-2099, 00-19 → 2000-2019
                                    if year_suffix >= 20:
                                        year = 2000 + year_suffix
                                    else:
                                        year = 2000 + year_suffix
                                    
                                    return pd.Timestamp(year=year, month=month, day=day)
                            else:
                                # 如果不是预期格式，尝试标准解析
                                return pd.to_datetime(date_str, errors='coerce')
                        except Exception as e:
                            return pd.NaT
                    
                    # 应用日期转换（避免SettingWithCopyWarning）
                    df = df.copy()
                    df[col] = df[col].apply(parse_date)
                    
                    # 数据验证：检查是否有异常日期
                    if col == 'booking_date':
                        valid_date_mask = (df[col].isna()) | ((df[col] >= pd.Timestamp('2020-01-01')) & (df[col] <= pd.Timestamp('2030-12-31')))
                        invalid_count = (~valid_date_mask).sum()
                        if invalid_count > 0:
                            logger.warning(f"发现 {invalid_count} 条异常的 {col} 数据，已过滤")
                            # 记录一些异常数据样本
                            invalid_dates = df[~valid_date_mask][col].head(5).tolist()
                            logger.warning(f"异常日期样本: {invalid_dates}")
                            df = df[valid_date_mask]

            return df
        except Exception as e:
            logger.error(f"处理HID数据失败: {e}")
            return pd.DataFrame()

    def read_all_inv(self, complete_month: int = 0) -> pd.DataFrame:
        """
        读取所有发票文件并处理数据

        Args:
            complete_month: 完整月份的截止时间，格式为 'yyyymm'

        Returns:
            DataFrame: 合并后的发票数据
        """
        if not self._invoice_path.exists():
            logger.warning(f"Invoice文件夹不存在: {self._invoice_path}")
            return pd.DataFrame()

        datas = pd.DataFrame()
        successful_files = []
        failed_files = []
        skipped_files = []

        try:
            files = [f for f in self._invoice_path.iterdir() if f.is_file() and f.suffix.lower() in ['.xls', '.xlsx']]

            for file_path in files:
                filename = file_path.stem
                
                # 检查文件名格式（前6位为年月）
                if len(filename) < 6:
                    skipped_files.append(filename)
                    continue
                
                try:
                    y = int(filename[:6])
                    if y <= complete_month:
                        skipped_files.append(filename)
                        continue
                
                except ValueError:
                    logger.warning(f"⚠️ 文件名格式错误，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    df = self._read_excel_file(file_path)
                    if not df.empty:
                        processed_df = self._process_invoice_data(df)
                        if not processed_df.empty:
                            datas = pd.concat([datas, processed_df], ignore_index=True)
                            successful_files.append(filename)
                        else:
                            failed_files.append(f"{filename} (处理后数据为空)")
                            logger.warning(f"文件处理后数据为空: {filename}")
                    else:
                        failed_files.append(f"{filename} (读取后数据为空)")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)})")

            return datas

        except Exception as e:
            logger.error(f"读取Invoice文件失败: {e}")
            return pd.DataFrame()

    def read_all_hid(self, complete_month: int = 0) -> pd.DataFrame:
        """
        读取所有HID文件并处理数据

        Args:
            complete_month: 完整月份的截止时间，格式为 'yyyymm'

        Returns:
            DataFrame: 合并后的HID数据
        """
        if not self._hid_path.exists():
            logger.warning(f"HID文件夹不存在: {self._hid_path}")
            return pd.DataFrame()

        datas = pd.DataFrame()
        successful_files = []
        failed_files = []
        skipped_files = []

        try:
            files = [f for f in self._hid_path.iterdir() if f.is_file() and f.suffix.lower() in ['.xls', '.xlsx']]

            for file_path in files:
                # 检查文件名格式（前6位为年月）
                filename = file_path.stem
                if len(filename) < 6:
                    skipped_files.append(filename)
                    continue

                try:
                    y = int(filename[:6])
                    if y <= complete_month:
                        skipped_files.append(filename)
                        continue

                except ValueError:
                    logger.warning(f"⚠️ 文件名格式错误，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    df = self._read_excel_file(file_path)
                    if not df.empty:
                        processed_df = self._process_hid_data(df)
                        if not processed_df.empty:
                            datas = pd.concat([datas, processed_df], ignore_index=True)
                            successful_files.append(filename)
                        else:
                            failed_files.append(f"{filename} (处理后数据为空)")
                            logger.warning(f"文件处理后数据为空: {filename}")
                    else:
                        failed_files.append(f"{filename} (读取后数据为空)")
                        logger.warning(f"文件读取后数据为空: {filename}")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)})")
                    logger.error(f"处理文件失败: {filename}, 错误: {e}")

            return datas

        except Exception as e:
            logger.error(f"读取HID文件失败: {e}")
            return pd.DataFrame()

    def read_disputed(self) -> List[int]:
        """
        读取争议账单文件

        Returns:
            List[int]: 包含争议账单HID的列表
        """
        try:
            if not self._disputed_file.exists():
                logger.warning(f"争议账单文件不存在: {self._disputed_file}")
                return []

            with open(self._disputed_file, 'r') as file:
                data = pd.read_csv(file, header=None)

            if data.empty:
                return []

            # 转换为整数列表
            disputed_list = data[0].astype(int).tolist()
            logger.info(f"读取到 {len(disputed_list)} 个争议账单")
            return disputed_list

        except Exception as e:
            logger.error(f"读取争议账单文件失败: {e}")
            return []

    def _get_complete_month(self) -> int:
        """
        获取账单完成的月份

        Returns:
            int: 完成月份
        """
        try:
            if not self._complete_file.exists():
                logger.warning(f"完成进度文件不存在: {self._complete_file}")
                logger.info("将读取所有HID文件（无过滤）")
                return 0

            with open(self._complete_file, 'r', encoding='utf-8') as cm_file:
                content = cm_file.readline().strip()
                if not content:
                    logger.warning("complete.txt文件为空")
                    return 0

                complete_month = int(content)
                logger.info(f"从complete.txt读取到完成月份: {complete_month}")
                return complete_month

        except ValueError as e:
            logger.error(f"complete.txt文件内容格式错误，应为数字格式(如202411): {e}")
            return 0
        except Exception as e:
            logger.error(f"读取完成进度文件失败: {e}")
            return 0

    def _update_complete_month(self, last_month: str):
        """
        更新账单完成进度

        Args:
            last_month: 最新月份
        """
        try:
            self._complete_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._complete_file, 'w') as f:
                f.write(last_month)
            logger.info(f"更新完成进度: {last_month}")
        except Exception as e:
            logger.error(f"更新完成进度失败: {e}")

    def find_no_inv_booking(self, pre_month: str = '2025-07') -> Tuple[int, int]:
        """
        查找未开具发票的预订信息，并计算利润总额
        
        计算逻辑：
        1. 读取 complete_month 之后的 HID 数据（这个月份之后的所有业绩）
        2. 读取 所有 Invoice 数据（不过滤）
        3. 筛选：HID - Invoice = 未结算订单
        4. 返回：(complete_month之后的总利润, 未结算利润)

        Args:
            pre_month: 废弃参数，保留兼容性

        Returns:
            Tuple[int, int]: (complete_month之后的总利润, 未结算利润)
        """
        try:
            # 获取账单完成的月份信息
            complete_month = self._get_complete_month()

            # 两者都只读取 complete_month 之后的文件
            hid = self.read_all_hid(complete_month)
            inv = self.read_all_inv(complete_month)
            
            # 保存complete_month之后的所有HID数据（筛选前）
            if hid.empty:
                logger.warning("HID数据为空，无法继续")
                return 0, 0
            
            # 检查HID数据中是否有重复并去重
            hid_unique_count = hid['hid'].nunique()
            hid_total_count = len(hid)
            duplicate_count = hid_total_count - hid_unique_count
            
            if duplicate_count > 0:
                hid = hid.drop_duplicates(subset=['hid'], keep='first')
            
            hid_all_after_complete = hid.copy()
            total_profit_after_complete = hid_all_after_complete['profit'].sum()

            # 检查Invoice数据中是否有重复并去重
            if not inv.empty:
                inv_unique_count = inv['hid'].nunique()
                inv_total_count = len(inv)
                inv_duplicate_count = inv_total_count - inv_unique_count
                
                if inv_duplicate_count > 0:
                    inv = inv.drop_duplicates(subset=['hid'], keep='first')
            
            # 清除不正常订单：去除发票中已存在的订单
            if not inv.empty:
                # 确保数据类型一致（都转换为整数）
                hid['hid'] = pd.to_numeric(hid['hid'], errors='coerce').fillna(0).astype(int)
                inv['hid'] = pd.to_numeric(inv['hid'], errors='coerce').fillna(0).astype(int)
                
                # 执行筛选
                hid = hid[~hid['hid'].isin(inv['hid'])]

            # 清除已经发现有争议订单
            disputed = self.read_disputed()

            if disputed:
                hid = hid[~hid['hid'].isin(disputed)]

            if hid.empty:
                logger.warning("过滤后没有剩余HID数据，所有订单都已结算")
                # 所有订单都已结算，更新complete.txt
                if not hid_all_after_complete.empty:
                    latest_date = hid_all_after_complete['booking_date'].max()
                    if pd.notna(latest_date):
                        latest_month_str = latest_date.strftime('%Y%m')
                        current_complete = self._get_complete_month()
                        if int(latest_month_str) > current_complete:
                            self._update_complete_month(latest_month_str)
                return int(total_profit_after_complete), 0
            
            # 排序和计算
            hid = hid.sort_values(by=['booking_date', 'hid']).reset_index(drop=True)
            
            # 计算已结算利润（complete_month之后，已在Invoice中的订单）
            if not inv.empty and not hid_all_after_complete.empty:
                hid_all_after_complete['hid'] = pd.to_numeric(hid_all_after_complete['hid'], errors='coerce').fillna(0).astype(int)
                settled_hid = hid_all_after_complete[hid_all_after_complete['hid'].isin(inv['hid'])]
                settled_profit = settled_hid['profit'].sum()
            else:
                settled_profit = 0
            
            # 未结算利润（已在前面筛选过的hid数据）
            unsettled_profit = hid['profit'].sum()

            # 更新做账进度：找到最早的未结算订单月份的前一个月
            if not hid.empty:
                first_date = hid['booking_date'].iloc[0]
                
                if pd.notna(first_date):
                    first_year = first_date.year
                    first_month = first_date.month
                    
                    # 计算前一个月（即最后一个完全结算的月份）
                    if first_month == 1:
                        completed_year = first_year - 1
                        completed_month = 12
                    else:
                        completed_year = first_year
                        completed_month = first_month - 1
                    
                    completed_month_str = f"{completed_year}{completed_month:02d}"
                    current_complete = self._get_complete_month()
                    
                    if int(completed_month_str) > current_complete:
                        self._update_complete_month(completed_month_str)

            return int(total_profit_after_complete), int(settled_profit)

        except Exception as e:
            logger.error(f"计算未结算业绩失败: {e}")
            return 0, 0

    def export_unsettled_orders(self, output_path: str = None) -> bool:
        """
        导出未结算订单详细列表到Excel
        
        Args:
            output_path: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 获取账单完成的月份信息
            complete_month = self._get_complete_month()
            
            # 读取所有发票和预订信息
            inv = self.read_all_inv(complete_month)
            hid = self.read_all_hid(complete_month)
            
            if hid.empty:
                logger.warning("没有HID数据，无法导出")
                return False
            
            # 筛选未结算订单
            if not inv.empty:
                unsettled_hid = hid[~hid['hid'].isin(inv['hid'])]
            else:
                unsettled_hid = hid.copy()
            
            # 排除争议订单
            disputed = self.read_disputed()
            if disputed:
                unsettled_hid = unsettled_hid[~unsettled_hid['hid'].isin(disputed)]
            
            if unsettled_hid.empty:
                logger.info("所有订单都已结算，没有未结算订单")
                return False
            
            # 按订单日期排序
            unsettled_hid = unsettled_hid.sort_values(by=['booking_date', 'hid']).reset_index(drop=True)
            
            # 设置默认输出路径
            if output_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self._path / f"未结算订单_{timestamp}.xlsx"
            
            # 导出到Excel
            unsettled_hid.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"成功导出 {len(unsettled_hid)} 条未结算订单到: {output_path}")
            logger.info(f"未结算订单总利润: {unsettled_hid['profit'].sum()}")
            
            return True
            
        except Exception as e:
            logger.error(f"导出未结算订单失败: {e}")
            return False

    def export_settled_hid_summary(self, last_month: str = None) -> bool:
        """
        导出 last_month 以后已经结算的 HID 总结报告

        Args:
            last_month: 指定月份，格式为 'YYYYMM'，如果为 None 则使用 complete.txt 中的值

        Returns:
            bool: 导出是否成功
        """
        try:
            # 获取 last_month，如果未指定则从 complete.txt 读取
            if last_month is None:
                complete_month = self._get_complete_month()
                if complete_month == 0:
                    logger.error("无法获取 complete_month，请检查 complete.txt 文件")
                    return False
                    last_month = str(complete_month)

            # 读取所有发票数据
            inv_data = self.read_all_inv(complete_month=0)  # 读取所有发票数据

            if inv_data.empty:
                logger.warning("没有找到发票数据")
                return False

            # 确保 hdid_date 列存在
            if 'hdid_date' not in inv_data.columns:
                logger.error("发票数据中没有 'hdid_date' 列")
                return False

            # 过滤 last_month 以后的发票数据
            last_month_date = pd.to_datetime(last_month, format='%Y%m')
            settled_inv = inv_data[inv_data['hdid_date'] > last_month_date].copy()

            if settled_inv.empty:
                logger.warning(f"没有找到 {last_month} 以后已结算的发票数据")
                return False

            # 按 hid 排序
            settled_inv = settled_inv.sort_values(by=['hid']).reset_index(drop=True)

            # 计算总结统计
            summary_stats = {
                '总发票数量': len(settled_inv),
                '总毛收入': settled_inv['gross'].sum(),
                '总成本': settled_inv['cost'].sum(),
                '总利润': settled_inv['pl'].sum(),
                '平均利润率': (settled_inv['pl'].sum() / settled_inv['gross'].sum() * 100) if settled_inv[
                                                                                                  'gross'].sum() > 0 else 0,
                '最早结算日期': settled_inv['hdid_date'].min(),
                '最晚结算日期': settled_inv['hdid_date'].max(),
                '结算月份范围': f"{settled_inv['hdid_date'].min().strftime('%Y-%m')} 至 {settled_inv['hdid_date'].max().strftime('%Y-%m')}"
            }

            # 按月份分组统计
            monthly_stats = settled_inv.groupby(settled_inv['hdid_date'].dt.to_period('M')).agg({
                'hid': 'count',
                'gross': 'sum',
                'cost': 'sum',
                'pl': 'sum'
            }).rename(columns={
                'hid': '发票数量',
                'gross': '毛收入',
                'cost': '成本',
                'pl': '利润'
            })

            # 按公司分组统计
            company_stats = settled_inv.groupby('company').agg({
                'hid': 'count',
                'gross': 'sum',
                'cost': 'sum',
                'pl': 'sum'
            }).rename(columns={
                'hid': '发票数量',
                'gross': '毛收入',
                'cost': '成本',
                'pl': '利润'
            }).sort_values(by='利润', ascending=False)

            # 生成输出文件名
            output_filename = f"已结算HID总结_{last_month}_至_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx"
            output_path = self._path / output_filename

            # 创建 Excel 文件
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 写入详细数据
                settled_inv.to_excel(writer, sheet_name='详细数据', index=False)

                # 写入总结统计
                summary_df = pd.DataFrame([summary_stats])
                summary_df.to_excel(writer, sheet_name='总结统计', index=False)

                # 写入月度统计
                monthly_stats.to_excel(writer, sheet_name='月度统计')

                # 写入公司统计
                company_stats.to_excel(writer, sheet_name='公司统计')

            return True

        except Exception as e:
            logger.error(f"导出已结算 HID 总结报告失败: {e}")
            return False

    def generate_settled_summary(self, last_month: str = None) -> str:
        """
        生成已结算 HID 总结报告的便捷方法

        Args:
            last_month: 指定月份，格式为 'YYYYMM'，如果为 None 则使用 complete.txt 中的值

        Returns:
            str: 输出文件路径，如果失败则返回空字符串
        """
        try:
            success = self.export_settled_hid_summary(last_month)
            if success:
                # 获取输出文件路径
                if last_month is None:
                    complete_month = self._get_complete_month()
                    last_month = str(complete_month)

                output_filename = f"已结算HID总结_{last_month}_至_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx"
                output_path = self._path / output_filename

                if output_path.exists():
                    return str(output_path)

            return ""

        except Exception as e:
            logger.error(f"生成已结算总结报告失败: {e}")
            return ""


class CountMonth:
    """
    按月统计绩效数据的类
    """

    def __init__(self, start_month: int = 202304, end_month: int = 202307,
                 file_path: Optional[str] = None, name: str = "Zz"):
        """
        初始化CountMonth类

        Args:
            start_month: 起始月份，格式为 YYYYMM
            end_month: 结束月份，格式为 YYYYMM
            file_path: 文件路径，默认为None
            name: 名称，用于构建默认路径
        """
        if file_path:
            self._path = Path(file_path)
        else:
            self._path = Path(f'E:/WORKING/B-账单/BOOKING/{name}')

        self.start_month = start_month
        self.end_month = end_month
        self._hid_path = self._path / "HID"

        # 获取HID数据表头配置
        self.hid_headers = get_report_headers('order_report')  # 改为使用 order_report

        # 验证路径
        self._validate_paths()

    def _validate_paths(self):
        """验证必要的文件夹路径是否存在"""
        if not self._path.exists():
            raise FileNotFoundError(f"路径不存在: {self._path}")

        if not self._hid_path.exists():
            logger.warning(f"HID文件夹不存在: {self._hid_path}")

    def import_my_performance(self) -> pd.DataFrame:
        """
        导入绩效数据，遍历文件夹中的Excel文件，过滤出符合月份范围的数据

        Returns:
            DataFrame: 包含清理后绩效数据的DataFrame
        """
        if not self._hid_path.exists():
            logger.warning(f"HID文件夹不存在: {self._hid_path}")
            return pd.DataFrame()

        performance = pd.DataFrame()
        successful_files = []
        failed_files = []
        skipped_files = []

        try:
            files = [f for f in self._hid_path.iterdir() if f.is_file() and f.suffix.lower() in ['.xls', '.xlsx']]

            for file_path in files:
                # 检查文件名格式（前6位为年月）
                filename = file_path.stem
                if len(filename) < 6:
                    skipped_files.append(filename)
                    continue

                try:
                    y = int(filename[:6])
                    if y < self.start_month or y > self.end_month:
                        skipped_files.append(filename)
                        continue
                except ValueError:
                    logger.warning(f"文件名格式错误，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    df = self._read_excel_file(file_path)
                    if not df.empty:
                        processed_df = self._process_performance_data(df)
                        if not processed_df.empty:
                            performance = pd.concat([performance, processed_df], ignore_index=True)
                            successful_files.append(filename)
                        else:
                            failed_files.append(f"{filename} (处理后数据为空)")
                            logger.warning(f"文件处理后数据为空: {filename}")
                    else:
                        failed_files.append(f"{filename} (读取后数据为空)")
                        logger.warning(f"文件读取后数据为空: {filename}")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)})")
                    logger.error(f"处理文件失败: {filename}, 错误: {e}")

            if not performance.empty:
                # 按日期和编号排序
                performance = performance.sort_values(by=['order_date', 'hid']).reset_index(drop=True)

                # 格式化月份
                performance['order_date'] = pd.to_datetime(performance['order_date'])
                performance['month'] = performance['order_date'].dt.strftime('%Y-%m')

                # 获取首尾HID
                hids = performance['hid'].values
                if len(hids) > 0:
                    first_hid = hids[0]
                    last_hid = hids[-1]
                    performance['firstHid'] = first_hid
                    performance['lastHid'] = last_hid

            return performance

        except Exception as e:
            logger.error(f"导入绩效数据失败: {e}")
            return pd.DataFrame()

    def _read_excel_file(self, file_path: Path, sheet_name: str = 'Sheet1') -> pd.DataFrame:
        """
        安全读取Excel文件

        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称

        Returns:
            DataFrame: 读取的数据
        """
        try:
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return pd.DataFrame()

            # 读取Excel时禁用日期自动解析，将所有数据作为字符串读取
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            # 立即将所有列转换为字符串，避免自动日期解析
            df = df.astype(str)
            return df
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return pd.DataFrame()

    def _process_performance_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理绩效数据，应用列映射和清理
        """
        if df.empty:
            return df

        try:
            # 应用表头
            if len(df.columns) == len(self.hid_headers) + 1:
                extended_headers = self.hid_headers + ['additional_info']
                df.columns = extended_headers
            else:
                logger.warning(f"绩效数据列数({len(df.columns)})与表头数({len(self.hid_headers)})不匹配")
                # 使用默认列名
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
            # 只用列名处理
            df = df.dropna(subset=['hid'])
            if df.empty:
                return df
            # 数字列转换
            numeric_cols = ['hid', 'selling_price', 'cost_price', 'profit']
            for col in numeric_cols:
                if col in df.columns:
                    df.loc[:, col] = pd.to_numeric(df.loc[:, col], errors='coerce').fillna(0).astype(int)

            # 字符串列转换
            str_cols = ['customer_name', 'product_name', 'booking_type', 'created_by', 'additional_info']
            for col in str_cols:
                if col in df.columns:
                    # 使用更安全的方式转换字符串
                    df.loc[:, col] = df.loc[:, col].fillna('').astype(str)

            # 处理日期列 - 转换新加坡日期格式
            # 按照新规则：原来年份的后两位作为新的日期，原来日期前面加上"20"变成新的年份
            # 例如："2029/7/25" -> "29/7/2025"
            date_cols = ['order_date', 'travel_date', 'created_date']
            for col in date_cols:
                if col in df.columns:
                    # 先转换为字符串，然后应用转换规则
                    df[col] = df[col].astype(str)
                    # 只处理包含 '/' 的日期格式
                    mask = df[col].str.contains('/', na=False)
                    if mask.any():
                        # 对包含 '/' 的日期应用转换
                        df.loc[mask, col] = df.loc[mask, col].apply(self._convert_singapore_date)

            return df
        except Exception as e:
            logger.error(f"处理绩效数据失败: {e}")
            return pd.DataFrame()


if __name__ == '__main__':
    # name = "Ly"
    # name = name
    booking_path = "E:\\Project\\MyTravelPanel\\资源\\账单\\BOOKING"
    count = CountHid(booking_path)
    count.find_no_inv_booking()
    # count.export_settled_hid_summary()
