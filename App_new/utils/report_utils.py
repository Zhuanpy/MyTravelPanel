"""
报表处理工具模块
提供报表相关的工具函数，包括表头处理、文件读取等功能
"""

import pandas as pd
from App_new.config import Config
import tempfile
import os


def get_report_headers(header_type='order_report'):
    """
    获取指定类型的报表表头
    
    Args:
        header_type (str): 表头类型，可选值：
            - 'order_report': 标准订单报表（16个字段）
            - 'simple_order_report': 简化订单报表（9个字段）
            - 'financial_report': 财务报表（6个字段）
    
    Returns:
        list: 表头列表
    """
    return Config.get_header_list(header_type)


def get_report_headers_string(header_type='order_report'):
    """
    获取指定类型的报表表头字符串（用逗号分隔）
    
    Args:
        header_type (str): 表头类型
    
    Returns:
        str: 表头字符串
    """
    return Config.get_header_string(header_type)


def read_excel_file(file_path, header_type='order_report', has_header=False):
    """
    读取Excel文件并应用表头
    
    Args:
        file_path (str): 文件路径
        header_type (str): 表头类型
        has_header (bool): 文件是否已有表头
    
    Returns:
        pandas.DataFrame: 处理后的数据框
    """
    try:
        headers = get_report_headers(header_type)
        
        if has_header:
            # 文件已有表头，直接读取
            df = pd.read_excel(file_path)
        else:
            # 文件没有表头，使用配置的表头
            df = pd.read_excel(file_path, header=None, names=headers)
        
        return df
    except Exception as e:
        raise Exception(f"读取Excel文件失败: {str(e)}")


def read_csv_file(file_path, header_type='order_report', has_header=False, encoding='utf-8'):
    """
    读取CSV文件并应用表头
    
    Args:
        file_path (str): 文件路径
        header_type (str): 表头类型
        has_header (bool): 文件是否已有表头
        encoding (str): 文件编码
    
    Returns:
        pandas.DataFrame: 处理后的数据框
    """
    try:
        headers = get_report_headers(header_type)
        
        if has_header:
            # 文件已有表头，直接读取
            df = pd.read_csv(file_path, encoding=encoding)
        else:
            # 文件没有表头，使用配置的表头
            df = pd.read_csv(file_path, header=None, names=headers, encoding=encoding)
        
        return df
    except Exception as e:
        raise Exception(f"读取CSV文件失败: {str(e)}")


def save_report_with_headers(df, output_path, header_type='order_report'):
    """
    保存报表文件，确保包含正确的表头
    
    Args:
        df (pandas.DataFrame): 数据框
        output_path (str): 输出文件路径
        header_type (str): 表头类型
    """
    try:
        # 确保数据框有正确的列名
        expected_headers = get_report_headers(header_type)
        
        if len(df.columns) != len(expected_headers):
            raise ValueError(f"数据列数({len(df.columns)})与期望表头数({len(expected_headers)})不匹配")
        
        # 设置列名
        df.columns = expected_headers
        
        # 根据文件扩展名保存
        if output_path.lower().endswith('.csv'):
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(output_path, index=False)
            
    except Exception as e:
        raise Exception(f"保存报表文件失败: {str(e)}")


def compare_profit_columns(df_a, df_b, profit_column='profit', id_column=None):
    """
    对比两个数据框的利润列
    
    Args:
        df_a (pandas.DataFrame): 报表A
        df_b (pandas.DataFrame): 报表B
        profit_column (str): 利润列名
        id_column (str): 标识列名，如果为None则使用第一列
    
    Returns:
        dict: 对比结果
    """
    try:
        if id_column is None:
            id_column = df_a.columns[0]
        
        # 创建数据字典
        data_a = {}
        data_b = {}
        
        # 处理报表A
        for _, row in df_a.iterrows():
            item_id = str(row[id_column]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):
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
            item_id = str(row[id_column]).strip()
            profit_value = row[profit_column]
            if pd.notna(profit_value):
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
        
        # 统计信息
        summary = {
            'total_a': len(data_a),
            'total_b': len(data_b),
            'matched': len(all_items) - len(differences),
            'differences': len(differences)
        }
        
        return {
            'success': True,
            'differences': differences,
            'summary': summary
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def add_comparison_column(df_a, df_b, profit_column='profit', id_column=None):
    """
    为两个数据框添加对比列
    
    Args:
        df_a (pandas.DataFrame): 报表A
        df_b (pandas.DataFrame): 报表B
        profit_column (str): 利润列名
        id_column (str): 标识列名
    
    Returns:
        tuple: (df_a_with_column, df_b_with_column)
    """
    if id_column is None:
        id_column = df_a.columns[0]
    
    # 创建数据字典用于对比
    data_a = {}
    data_b = {}
    
    # 处理报表A
    for _, row in df_a.iterrows():
        item_id = str(row[id_column]).strip()
        profit_value = row[profit_column]
        if pd.notna(profit_value):
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
        item_id = str(row[id_column]).strip()
        profit_value = row[profit_column]
        if pd.notna(profit_value):
            try:
                # 尝试转换为浮点数
                float_value = float(profit_value)
                data_b[item_id] = float_value
            except (ValueError, TypeError):
                # 如果转换失败，记录警告并跳过
                print(f"警告：报表B中项目 {item_id} 的利润值 '{profit_value}' 无法转换为数字，已跳过")
                continue
    
    # 为报表A添加对比列
    df_a_copy = df_a.copy()
    df_a_copy['数据一致性'] = '否'
    for idx, row in df_a_copy.iterrows():
        item_id = str(row[id_column]).strip()
        value_a = data_a.get(item_id, 0)
        value_b = data_b.get(item_id, 0)
        if abs(value_a - value_b) <= 0.01:
            df_a_copy.at[idx, '数据一致性'] = '是'
    
    # 为报表B添加对比列
    df_b_copy = df_b.copy()
    df_b_copy['数据一致性'] = '否'
    for idx, row in df_b_copy.iterrows():
        item_id = str(row[id_column]).strip()
        value_a = data_a.get(item_id, 0)
        value_b = data_b.get(item_id, 0)
        if abs(value_a - value_b) <= 0.01:
            df_b_copy.at[idx, '数据一致性'] = '是'
    
    return df_a_copy, df_b_copy


class BatchReportComparer:
    """批量报表对比工具类 - 重新设计版本"""
    
    def __init__(self, header_type='order_report'):
        """
        初始化批量报表对比器
        
        Args:
            header_type (str): 表头类型
        """
        self.header_type = header_type
        self.headers = get_report_headers(header_type)
        self.header_string = get_report_headers_string(header_type)
    
    def get_filename_without_extension(self, filename):
        """获取不带扩展名的文件名"""
        return os.path.splitext(filename)[0]
    
    def group_files_by_name(self, files):
        """
        按文件名分组文件（不考虑扩展名）
        
        Args:
            files: 文件列表
            
        Returns:
            dict: 按文件名分组的文件字典
        """
        grouped_files = {}
        
        for file in files:
            if hasattr(file, 'filename'):
                filename = file.filename
            else:
                filename = str(file)
            
            # 获取不带扩展名的文件名作为key
            name_key = self.get_filename_without_extension(filename)
            if name_key not in grouped_files:
                grouped_files[name_key] = []
            grouped_files[name_key].append(file)
        
        return grouped_files
    
    def read_report_file(self, file):
        """
        读取单个报表文件
        
        Args:
            file: 文件对象
            
        Returns:
            pandas.DataFrame: 读取的数据框
        """
        try:
            filename = file.filename if hasattr(file, 'filename') else str(file)
            
            # 检查文件对象是否有read方法（Flask文件对象）
            if hasattr(file, 'read'):
                # 重置文件指针到开始位置
                file.seek(0)
                
                if filename.lower().endswith('.csv'):
                    df = pd.read_csv(file, encoding='utf-8', header=None, names=self.headers)
                else:
                    # Excel文件
                    try:
                        df = pd.read_excel(file, header=None, names=self.headers, engine='openpyxl')
                    except:
                        try:
                            df = pd.read_excel(file, header=None, names=self.headers, engine='xlrd')
                        except:
                            df = pd.read_excel(file, header=None, names=self.headers)
            else:
                # 处理文件路径或MockFile对象
                if hasattr(file, 'filepath'):
                    # MockFile对象
                    filepath = file.filepath
                else:
                    # 普通文件路径
                    filepath = str(file)
                
                if filename.lower().endswith('.csv'):
                    df = pd.read_csv(filepath, encoding='utf-8', header=None, names=self.headers)
                else:
                    try:
                        df = pd.read_excel(filepath, header=None, names=self.headers, engine='openpyxl')
                    except:
                        try:
                            df = pd.read_excel(filepath, header=None, names=self.headers, engine='xlrd')
                        except:
                            df = pd.read_excel(filepath, header=None, names=self.headers)
            
            return df
        except Exception as e:
            print(f"读取文件失败 {filename}: {str(e)}")
            return None
    
    def compare_reports_by_filename(self, files_a, files_b):
        """
        按文件名对比报表
        
        Args:
            files_a (list): 文件夹A的文件列表
            files_b (list): 文件夹B的文件列表
            
        Returns:
            dict: 对比结果
        """
        # 按文件名分组
        grouped_a = self.group_files_by_name(files_a)
        grouped_b = self.group_files_by_name(files_b)
        
        # 统一差异记录列表
        all_differences = []
        
        # 统计信息
        stats = {
            'total_files_a': len(files_a),
            'total_files_b': len(files_b),
            'matched_pairs': 0,
            'different_pairs': 0,
            'missing_in_b': 0,
            'missing_in_a': 0
        }
        
        # 对比每个文件名
        for filename_key in grouped_a:
            files_a_group = grouped_a[filename_key]
            files_b_group = grouped_b.get(filename_key, [])
            
            if not files_b_group:
                # A中有B中没有的文件
                stats['missing_in_b'] += len(files_a_group)
                for file_a in files_a_group:
                    df_a = self.read_report_file(file_a)
                    if df_a is not None:
                        # 记录A有B无的所有order_id
                        for _, row in df_a.iterrows():
                            order_id = str(row['hid']).strip()
                            profit_a = row['profit']
                            all_differences.append({
                                'order_id': order_id,
                                '所属文件A': file_a.filename if hasattr(file_a, 'filename') else str(file_a),
                                '所属文件B': '',
                                'A利润': profit_a,
                                'B利润': '',
                                '差异说明': f'报表A含有order_id {order_id}，报表B缺少该order_id'
                            })
                continue
            
            # 对比该文件名的报表
            for file_a in files_a_group:
                df_a = self.read_report_file(file_a)
                if df_a is None:
                    continue
                
                # 寻找对应的B文件（取第一个匹配的）
                matched_b_file = files_b_group[0] if files_b_group else None
                
                if matched_b_file:
                    df_b = self.read_report_file(matched_b_file)
                    if df_b is not None:
                        # 对比这两个报表
                        comparison_result = self._compare_single_pair_new(
                            df_a, df_b, file_a, matched_b_file
                        )
                        
                        if comparison_result:  # 如果有差异
                            stats['different_pairs'] += 1
                            all_differences.extend(comparison_result)
                        else:
                            stats['matched_pairs'] += 1
                else:
                    # 没有找到对应的B文件
                    stats['missing_in_b'] += 1
        
        # 检查B中有A中没有的文件
        for filename_key in grouped_b:
            if filename_key not in grouped_a:
                files_b_group = grouped_b[filename_key]
                stats['missing_in_a'] += len(files_b_group)
                
                for file_b in files_b_group:
                    df_b = self.read_report_file(file_b)
                    if df_b is not None:
                        # 记录B有A无的所有order_id
                        for _, row in df_b.iterrows():
                            order_id = str(row['hid']).strip()
                            profit_b = row['profit']
                            all_differences.append({
                                'order_id': order_id,
                                '所属文件A': '',
                                '所属文件B': file_b.filename if hasattr(file_b, 'filename') else str(file_b),
                                'A利润': '',
                                'B利润': profit_b,
                                '差异说明': f'报表B含有order_id {order_id}，报表A缺少该order_id'
                            })
        
        return {
            'summary': stats,
            'differences': all_differences
        }
    
    def _compare_single_pair_new(self, df_a, df_b, file_a, file_b):
        def filter_summary_rows(df):
            keywords = ['Grand Tot', '合计', 'Total']
            mask = ~df.apply(lambda row: any(kw.lower() in str(cell).lower() for kw in keywords for cell in row), axis=1)
            df = df[mask]
            df = df[df['order_id'].apply(lambda x: str(x).isdigit())]
            return df
        def get_info(df, hid, col):
            try:
                val = df[df['order_id'] == hid][col].values
                if len(val) > 0:
                    return val[0]
            except Exception:
                pass
            return ''
        try:
            differences = []
            print('调试: df_a[order_id]原始:', list(df_a['order_id'])[:10])
            df_a['order_id'] = df_a['order_id'].apply(lambda x: str(x).split('.')[0].strip())
            print('调试: df_a[order_id]处理后:', list(df_a['order_id'])[:10])
            df_b['order_id'] = df_b['order_id'].apply(lambda x: str(x).split('.')[0].strip())
            print('调试: df_b[order_id]处理后:', list(df_b['order_id'])[:10])
            df_a = filter_summary_rows(df_a)
            df_b = filter_summary_rows(df_b)
            all_hids_a = set(df_a['order_id'])
            all_hids_b = set(df_b['order_id'])
            print(f"调试: all_hids_a={all_hids_a}")
            print(f"调试: all_hids_b={all_hids_b}")
            common_hids = all_hids_a & all_hids_b
            print(f"调试: common_hids={common_hids}")
            print("调试: 遍历 common_hids:", list(common_hids))
            for hid in common_hids:
                print(f"调试: 当前hid={repr(hid)}, 类型={type(hid)}, 长度={len(hid)}")
                if hid == '132172':
                    print("调试: 命中 132172 !!!")
                elif '132172' in str(hid):
                    print(f"调试: 包含132172的hid: {repr(hid)}")
                profit_a = df_a[df_a['order_id'] == hid]['profit'].values[0]
                profit_b = df_b[df_b['order_id'] == hid]['profit'].values[0]
                # 新增字段
                customer_type = get_info(df_a, hid, 'customer_type') or get_info(df_b, hid, 'customer_type')
                passenger_name = get_info(df_a, hid, 'passenger_name') or get_info(df_b, hid, 'passenger_name')
                product_name = get_info(df_a, hid, 'product_name') or get_info(df_b, hid, 'product_name')
                print(f"调试: HID={hid}, A利润={profit_a}({type(profit_a)}), B利润={profit_b}({type(profit_b)})")
                try:
                    diff = abs(float(profit_a) - float(profit_b))
                    if diff > 0.01:  # 允许0.01的误差
                        differences.append({
                            'order_id': hid,
                            'customer_type': customer_type,
                            'passenger_name': passenger_name,
                            'product_name': product_name,
                            '所属文件A': file_a.filename if hasattr(file_a, 'filename') else str(file_a),
                            '所属文件B': file_b.filename if hasattr(file_b, 'filename') else str(file_b),
                            'A利润': profit_a,
                            'B利润': profit_b,
                            '差异说明': f'报表A中order_id {hid}利润为{profit_a}，报表B中利润为{profit_b}，差异{float(profit_b) - float(profit_a):.2f}',
                            '差异类型': '利润差异',
                            '是否核查': '',
                            '是否正常': ''
                        })
                        print(f"调试: 发现差异! HID={hid}, 差异={diff}")
                except Exception as e:
                    print(f"调试: 转换异常 HID={hid}, 错误={e}")
                    continue
            # A有B无的order_id
            missing_in_b = all_hids_a - all_hids_b
            for hid in missing_in_b:
                profit_a = df_a[df_a['order_id'] == hid]['profit'].values[0]
                customer_type = get_info(df_a, hid, 'customer_type')
                passenger_name = get_info(df_a, hid, 'passenger_name')
                product_name = get_info(df_a, hid, 'product_name')
                differences.append({
                    'order_id': hid,
                    'customer_type': customer_type,
                    'passenger_name': passenger_name,
                    'product_name': product_name,
                    '所属文件A': file_a.filename if hasattr(file_a, 'filename') else str(file_a),
                    '所属文件B': file_b.filename if hasattr(file_b, 'filename') else str(file_b),
                    'A利润': profit_a,
                    'B利润': '',
                    '差异说明': f'报表A含有order_id {hid}，报表B缺少该order_id',
                    '差异类型': '缺失差异',
                    '是否核查': '',
                    '是否正常': ''
                })
            # B有A无的order_id
            missing_in_a = all_hids_b - all_hids_a
            for hid in missing_in_a:
                profit_b = df_b[df_b['order_id'] == hid]['profit'].values[0]
                customer_type = get_info(df_b, hid, 'customer_type')
                passenger_name = get_info(df_b, hid, 'passenger_name')
                product_name = get_info(df_b, hid, 'product_name')
                differences.append({
                    'order_id': hid,
                    'customer_type': customer_type,
                    'passenger_name': passenger_name,
                    'product_name': product_name,
                    '所属文件A': file_a.filename if hasattr(file_a, 'filename') else str(file_a),
                    '所属文件B': file_b.filename if hasattr(file_b, 'filename') else str(file_b),
                    'A利润': '',
                    'B利润': profit_b,
                    '差异说明': f'报表B含有order_id {hid}，报表A缺少该order_id',
                    '差异类型': '缺失差异',
                    '是否核查': '',
                    '是否正常': ''
                })
            return differences
        except Exception as e:
            print(f"调试: _compare_single_pair_new 异常: {e}")
            return []
    
    def generate_excel_report_new(self, results, output_path=None):
        """
        生成新的Excel汇总报告
        
        Args:
            results (dict): 对比结果
            output_path (str): 输出路径
            
        Returns:
            str: 生成的报告文件路径
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            # 设置输出路径
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f'batch_report_comparison_{timestamp}.xlsx'
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 汇总sheet
                summary_data = []
                stats = results['summary']
                summary_data.append({
                    '报表类型': '汇总信息',
                    '文件夹A报表数量': stats['total_files_a'],
                    '文件夹B报表数量': stats['total_files_b'],
                    '成功对比的报表对': stats['matched_pairs'],
                    '发现差异的报表对': stats['different_pairs'],
                    'A中有B中无的文件数': stats['missing_in_b'],
                    'B中有A中无的文件数': stats['missing_in_a'],
                    '详细信息': ''
                })
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='批量对比报告', index=False)
                
                # 详细差异sheet
                if results['differences']:
                    df_details = pd.DataFrame(results['differences'])
                    df_details.to_excel(writer, sheet_name='详细差异', index=False)
                    
                    # 设置列宽
                    worksheet = writer.sheets['详细差异']
                    column_widths = [15, 25, 25, 15, 15, 50]
                    for i, width in enumerate(column_widths):
                        worksheet.column_dimensions[chr(65 + i)].width = width
                
                # 设置汇总sheet列宽
                worksheet = writer.sheets['批量对比报告']
                column_widths = [20, 25, 25, 25, 25, 25, 25, 50]
                for i, width in enumerate(column_widths):
                    worksheet.column_dimensions[chr(65 + i)].width = width
            
            return output_path
            
        except Exception as e:
            print(f"生成Excel报告失败: {str(e)}")
            return None 