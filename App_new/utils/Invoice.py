import pandas as pd
import os
import logging
from pathlib import Path
from typing import Tuple, Optional, List

from xlwt.ExcelMagic import ptgInt

from App.config import Config
from App.utils.report_utils import get_report_headers

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

            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            logger.debug(f"成功读取文件: {file_path}, 数据行数: {len(df)}")
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
            logger.debug(f"原始数据列数: {len(df.columns)}")

            # 应用表头
            if len(df.columns) == len(self.invoice_headers):
                df.columns = self.invoice_headers

            else:
                logger.warning(f"Invoice数据列数({len(df.columns)})与表头数({len(self.invoice_headers)})不匹配")
                # 使用默认列名
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
            # 只用列名处理
            # 删除关键列的空值行
            df = df.dropna(subset=['hid', 'inv'])

            if df.empty:
                return df

            # 整数字列转换
            numeric_cols = ['hid', 'inv']
            for col in numeric_cols:
                df.loc[:, col] = df[col].astype(int)

            # 浮点数字列转换
            numeric_cols = ['gross', 'total_gross', 'cost', 'pl', 'marg', 'bal', 'nett_cost']

            for col in numeric_cols:
                if col in df.columns:
                    df.loc[:, col] = pd.to_numeric(df.loc[:, col], errors='coerce').fillna(0).astype(float)

            # 字符串列转换（根据新的表头）
            str_cols = ['company', 'client_name', 'itin_Description', 'curr', 'consultant', 'sales_consultant',
                        'Description']

            for col in str_cols:
                if col in df.columns:
                    # 使用更安全的方式转换字符串
                    df.loc[:, col] = df.loc[:, col].fillna('').astype(str)

            # 处理日期列 - 转换新加坡日期格式
            # 按照新规则：原来年份的后两位作为新的日期，原来日期前面加上"20"变成新的年份
            # 例如："2029/7/25" -> "29/7/2025"
            date_cols = ['inv_date', 'order_date', 'travel_date', 'created_date', 'dep_date', 'hdid_date']
            for col in date_cols:
                if col in df.columns:
                    # 先转换为字符串，然后应用转换规则
                    df.loc[:, col] = df.loc[:, col].astype(str).str[2:]
                    df.loc[:, col] = pd.to_datetime(df.loc[:, col], format='%d-%m-%y')

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
            logger.debug(f"原始数据列数: {len(df.columns)}")
            # 应用表头
            if len(df.columns) == len(self.hid_headers):
                df.columns = self.hid_headers
                logger.debug(f"使用标准表头: {list(df.columns)}")
            else:
                logger.warning(f"HID数据列数({len(df.columns)})与表头数({len(self.hid_headers)})不匹配")
                # 使用默认列名
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
                logger.debug(f"使用默认表头: {list(df.columns)}")
            # 只用列名处理
            # 检查 'order_id' 列是否存在（order_report 中使用 order_id 而不是 hid）
            if 'order_id' in df.columns:
                df = df.dropna(subset=['order_id'])
            else:
                logger.warning("HID数据中没有找到 'order_id' 列，可用的列: " + str(list(df.columns)))
                # 如果没有 'order_id' 列，尝试使用第一列作为 order_id
                if len(df.columns) > 0:
                    df.columns.values[0] = 'order_id'
                    df = df.dropna(subset=['order_id'])
                else:
                    logger.error("HID数据为空或没有列")
                    return pd.DataFrame()

            if df.empty:
                return df
            # 数字列转换
            numeric_cols = ['order_id', 'selling_price', 'cost_price', 'profit']
            for col in numeric_cols:
                if col in df.columns:
                    df.loc[:, col] = pd.to_numeric(df.loc[:, col], errors='coerce').fillna(0).astype(int)

            str_cols = ['customer_name', 'product_name', 'booking_type', 'created_by']
            for col in str_cols:
                if col in df.columns:
                    # 使用更安全的方式转换字符串
                    df.loc[:, col] = df.loc[:, col].fillna('').astype(str)
            df = df.dropna(subset=['customer_type'])
            # 处理日期列 - 转换新加坡日期格式
            # 按照新规则：原来年份的后两位作为新的日期，原来日期前面加上"20"变成新的年份
            # 例如："2029/7/25" -> "29/7/2025"
            date_cols = ['order_date', 'travel_date']

            for col in date_cols:
                if col in df.columns:
                    # 先转换为字符串，然后应用转换规则
                    df[col] = df[col].astype(str).str[2:]
                    df.loc[:, col] = pd.to_datetime(df.loc[:, col], format='%d-%m-%y')

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
            logger.info(f"找到 {len(files)} 个Invoice文件")

            if complete_month > 0:
                logger.info(f"根据complete.txt过滤，只读取 {complete_month} 之后的文件")

            for file_path in files:
                # 检查文件名格式（前6位为年月）
                filename = file_path.stem
                if len(filename) < 6:
                    logger.debug(f"文件名格式不符合要求，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    y = int(filename[:6])
                    if y < complete_month:
                        logger.debug(f"文件 {filename} 在完成月份 {complete_month} 之前，跳过")
                        skipped_files.append(filename)
                        continue

                except ValueError:
                    logger.warning(f"文件名格式错误，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    df = self._read_excel_file(file_path)
                    if not df.empty:
                        processed_df = self._process_invoice_data(df)
                        if not processed_df.empty:
                            datas = pd.concat([datas, processed_df], ignore_index=True)
                            successful_files.append(filename)
                            logger.debug(f"成功导入文件: {filename} (记录数: {len(processed_df)})")
                        else:
                            failed_files.append(f"{filename} (处理后数据为空)")
                            logger.warning(f"文件处理后数据为空: {filename}")
                    else:
                        failed_files.append(f"{filename} (读取后数据为空)")
                        logger.warning(f"文件读取后数据为空: {filename}")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)})")
                    logger.error(f"处理文件失败: {filename}, 错误: {e}")

            # 输出详细的导入结果
            logger.info(f"Invoice文件导入完成:")
            logger.info(f"  - 成功导入: {len(successful_files)} 个文件")
            if successful_files:
                logger.info(f"  - 成功文件列表: {', '.join(successful_files)}")

            logger.info(f"  - 失败文件: {len(failed_files)} 个")
            if failed_files:
                logger.info(f"  - 失败文件列表: {', '.join(failed_files)}")

            logger.info(f"  - 跳过文件: {len(skipped_files)} 个")
            if skipped_files:
                logger.info(f"  - 跳过文件列表: {', '.join(skipped_files)}")

            logger.info(f"  - 总记录数: {len(datas)} 条")
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
            logger.info(f"找到 {len(files)} 个HID文件")

            if complete_month > 0:
                logger.info(f"根据complete.txt过滤，只读取 {complete_month} 之后的文件")

            for file_path in files:
                # 检查文件名格式（前6位为年月）
                filename = file_path.stem
                if len(filename) < 6:
                    logger.debug(f"文件名格式不符合要求，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    y = int(filename[:6])
                    if y < complete_month:
                        logger.debug(f"文件 {filename} 在完成月份 {complete_month} 之前，跳过")
                        skipped_files.append(filename)
                        continue

                except ValueError:
                    logger.warning(f"文件名格式错误，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    df = self._read_excel_file(file_path)
                    if not df.empty:
                        processed_df = self._process_hid_data(df)
                        if not processed_df.empty:
                            datas = pd.concat([datas, processed_df], ignore_index=True)
                            successful_files.append(filename)
                            logger.debug(f"成功导入文件: {filename} (记录数: {len(processed_df)})")
                        else:
                            failed_files.append(f"{filename} (处理后数据为空)")
                            logger.warning(f"文件处理后数据为空: {filename}")
                    else:
                        failed_files.append(f"{filename} (读取后数据为空)")
                        logger.warning(f"文件读取后数据为空: {filename}")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)})")
                    logger.error(f"处理文件失败: {filename}, 错误: {e}")

            # 输出详细的导入结果
            logger.info(f"HID文件导入完成:")
            logger.info(f"  - 成功导入: {len(successful_files)} 个文件")
            if successful_files:
                logger.info(f"  - 成功文件列表: {', '.join(successful_files)}")

            logger.info(f"  - 失败文件: {len(failed_files)} 个")
            if failed_files:
                logger.info(f"  - 失败文件列表: {', '.join(failed_files)}")

            logger.info(f"  - 跳过文件: {len(skipped_files)} 个")
            if skipped_files:
                logger.info(f"  - 跳过文件列表: {', '.join(skipped_files)}")

            logger.info(f"  - 总记录数: {len(datas)} 条")
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

        Args:
            pre_month: 指定的月份，用于过滤前几个月的订单，格式为 'YYYY-MM'

        Returns:
            Tuple[int, int]: 包含总利润和前几个月利润的元组 (profits, pre_sum)
        """
        try:
            # 获取账单完成的月份信息
            complete_month = self._get_complete_month()

            # 读取所有发票和预订信息
            inv = self.read_all_inv(complete_month)
            hid = self.read_all_hid(complete_month)

            print(inv.head())
            print(hid.head())

            print("INV pl Sum: ", inv['pl'].sum())
            print("HID profit Sum: ", hid['profit'].sum())

            # 清除不正常订单：去除发票中已存在的订单，且过滤掉盈利为0的订单
            if not inv.empty:
                hid = hid[~hid['order_id'].isin(inv['hid'])]  # 注意：Invoice 中仍使用 'hid'

            # 清除已经发现有争议订单
            disputed = self.read_disputed()

            if disputed:
                hid = hid[~hid['order_id'].isin(disputed)]

            if hid.empty:
                logger.warning("过滤后没有剩余HID数据")
                return 0, 0

            # 排序和计算
            hid = hid.sort_values(by=['order_id']).reset_index(drop=True)
            profits = hid['profit'].sum()

            # 获取最新做账进度，做账至几月份，并保存记录
            if not hid.empty:
                # 检查 order_date 是否为 NaT
                first_date = hid['order_date'].iloc[0]
                if pd.notna(first_date):  # 检查是否为 NaT
                    last_month = first_date.strftime('%Y%m')
                    self._update_complete_month(last_month)


                else:
                    logger.warning("第一个订单日期为 NaT，跳过进度更新")

            # 整理前几个月的订单并计算利润
            # 过滤掉 order_date 为 NaT 的记录
            valid_dates = hid[pd.notna(hid['order_date'])]

            if not valid_dates.empty:
                # 确保 pre_month 正确转换为 datetime 对象
                pre_month_date = pd.to_datetime(pre_month + '-01')  # 添加日期部分
                pre_booking = valid_dates[valid_dates['order_date'] < pre_month_date]
                pre_sum = pre_booking['profit'].sum()

            else:
                pre_sum = 0
                logger.warning("没有有效的订单日期，前几个月利润设为0")

            logger.info(f"计算完成 - 总利润: {profits}, 前{pre_month}利润: {pre_sum}")
            return int(profits), int(pre_sum)

        except Exception as e:
            logger.error(f"计算未结算业绩失败: {e}")
            return 0, 0

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

            logger.info(f"开始导出 {last_month} 以后已结算的 HID 总结报告")

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

            logger.info(f"已结算 HID 总结报告已保存到: {output_path}")
            logger.info(f"总结统计: {summary_stats}")

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
            logger.info(f"找到 {len(files)} 个HID文件")
            logger.info(f"过滤月份范围: {self.start_month} 到 {self.end_month}")

            for file_path in files:
                # 检查文件名格式（前6位为年月）
                filename = file_path.stem
                if len(filename) < 6:
                    logger.debug(f"文件名格式不符合要求，跳过: {filename}")
                    skipped_files.append(filename)
                    continue

                try:
                    y = int(filename[:6])
                    if y < self.start_month or y > self.end_month:
                        logger.debug(f"文件 {filename} 不在指定月份范围内，跳过")
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
                            logger.debug(f"成功导入文件: {filename} (记录数: {len(processed_df)})")
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
                performance = performance.sort_values(by=['order_date', 'order_id']).reset_index(
                    drop=True)  # 改为 order_id

                # 格式化月份
                performance['order_date'] = pd.to_datetime(performance['order_date'])
                performance['month'] = performance['order_date'].dt.strftime('%Y-%m')

                # 获取首尾HID
                order_ids = performance['order_id'].values  # 改为 order_id
                if len(order_ids) > 0:
                    first_order_id = order_ids[0]  # 改为 first_order_id
                    last_order_id = order_ids[-1]  # 改为 last_order_id
                    performance['firstOrderId'] = first_order_id  # 改为 firstOrderId
                    performance['lastOrderId'] = last_order_id  # 改为 lastOrderId

            # 输出详细的导入结果
            logger.info(f"绩效数据导入完成:")
            logger.info(f"  - 成功导入: {len(successful_files)} 个文件")
            if successful_files:
                logger.info(f"  - 成功文件列表: {', '.join(successful_files)}")

            logger.info(f"  - 失败文件: {len(failed_files)} 个")
            if failed_files:
                logger.info(f"  - 失败文件列表: {', '.join(failed_files)}")

            logger.info(f"  - 跳过文件: {len(skipped_files)} 个")
            if skipped_files:
                logger.info(f"  - 跳过文件列表: {', '.join(skipped_files)}")

            logger.info(f"  - 总记录数: {len(performance)} 条")

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

            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            logger.debug(f"成功读取文件: {file_path}, 数据行数: {len(df)}")
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
            logger.debug(f"原始数据列数: {len(df.columns)}")
            # 应用表头
            if len(df.columns) == len(self.hid_headers) + 1:
                extended_headers = self.hid_headers + ['additional_info']
                df.columns = extended_headers
            else:
                logger.warning(f"绩效数据列数({len(df.columns)})与表头数({len(self.hid_headers)})不匹配")
                # 使用默认列名
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
            # 只用列名处理
            df = df.dropna(subset=['order_id'])  # 改为 order_id
            if df.empty:
                return df
            # 数字列转换
            numeric_cols = ['order_id', 'selling_price', 'cost_price', 'profit']  # 改为 order_id
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
