# -*- coding: utf-8 -*-
"""
利润分配计算工具
根据盈亏金额范围计算操作员、业务员和公司的利润分配比例
"""

from decimal import Decimal
import math


def sigmoid(x):
    """
    Sigmoid函数（S型曲线），用于平滑过渡
    输入范围通常在[-6, 6]，输出范围在[0, 1]
    """
    return 1 / (1 + math.exp(-x))


def calculate_profit_ratios(profit):
    """
    根据盈亏金额计算利润分配比例
    
    参数:
        profit: 盈亏金额（SGD），负数代表亏损
    
    返回:
        tuple: (操作员比例, 业务员比例, 公司比例)
    """
    if profit is None:
        profit = Decimal('0')
    
    # 确保profit是Decimal类型
    if not isinstance(profit, Decimal):
        profit = Decimal(str(profit))
    
    profit_float = float(profit)
    
    # 负数（亏损）统一按照小单方案计算
    if profit_float < 0:
        return (Decimal('0.4'), Decimal('0.3'), Decimal('0.3'))
    
    # 小单：SGD 100以内（包括0）
    if profit_float <= 100:
        return (Decimal('0.4'), Decimal('0.3'), Decimal('0.3'))
    
    # 小单-中单过渡：SGD 100-200
    elif profit_float < 200:
        # 小单比例
        small_operator = Decimal('0.4')
        small_sales = Decimal('0.3')
        small_company = Decimal('0.3')
        
        # 中单比例
        medium_operator = Decimal('0.25')
        medium_sales = Decimal('0.35')
        medium_company = Decimal('0.4')
        
        # 使用sigmoid函数进行平滑过渡
        # 将100-200映射到sigmoid的输入范围[-6, 6]
        normalized = (profit_float - 100) / 100.0  # 0到1之间
        sigmoid_input = (normalized * 12) - 6  # 映射到[-6, 6]
        transition_factor = Decimal(str(sigmoid(sigmoid_input)))  # 转换为Decimal类型
        
        # 线性插值（更平滑的过渡）
        # transition_factor = Decimal(str(normalized))  # 简单的线性插值
        
        operator_ratio = small_operator + (medium_operator - small_operator) * transition_factor
        sales_ratio = small_sales + (medium_sales - small_sales) * transition_factor
        company_ratio = small_company + (medium_company - small_company) * transition_factor
        
        # 确保比例值被正确量化
        operator_ratio = operator_ratio.quantize(Decimal('0.0001'))
        sales_ratio = sales_ratio.quantize(Decimal('0.0001'))
        company_ratio = company_ratio.quantize(Decimal('0.0001'))
        
        return (operator_ratio, sales_ratio, company_ratio)
    
    # 中单：SGD 200-500
    elif profit_float < 500:
        return (Decimal('0.25'), Decimal('0.35'), Decimal('0.4'))
    
    # 中单-大单过渡：SGD 500-1000
    elif profit_float < 1000:
        # 中单比例
        medium_operator = Decimal('0.25')
        medium_sales = Decimal('0.35')
        medium_company = Decimal('0.4')
        
        # 大单比例
        large_operator = Decimal('0.2')
        large_sales = Decimal('0.4')
        large_company = Decimal('0.4')
        
        # 使用sigmoid函数进行平滑过渡
        # 将500-1000映射到sigmoid的输入范围[-6, 6]
        normalized = (profit_float - 500) / 500.0  # 0到1之间
        sigmoid_input = (normalized * 12) - 6  # 映射到[-6, 6]
        transition_factor = Decimal(str(sigmoid(sigmoid_input)))  # 转换为Decimal类型
        
        # 线性插值（更平滑的过渡）
        # transition_factor = Decimal(str(normalized))  # 简单的线性插值
        
        operator_ratio = medium_operator + (large_operator - medium_operator) * transition_factor
        sales_ratio = medium_sales + (large_sales - medium_sales) * transition_factor
        company_ratio = medium_company + (large_company - medium_company) * transition_factor
        
        # 确保比例值被正确量化
        operator_ratio = operator_ratio.quantize(Decimal('0.0001'))
        sales_ratio = sales_ratio.quantize(Decimal('0.0001'))
        company_ratio = company_ratio.quantize(Decimal('0.0001'))
        
        return (operator_ratio, sales_ratio, company_ratio)
    
    # 大单：SGD 1000以上
    else:
        return (Decimal('0.2'), Decimal('0.4'), Decimal('0.4'))


def get_order_type(profit):
    """
    根据盈亏金额获取订单类型
    
    参数:
        profit: 盈亏金额（SGD），负数代表亏损
    
    返回:
        str: 订单类型名称
    """
    if profit is None:
        return None
    
    if not isinstance(profit, Decimal):
        profit = Decimal(str(profit))
    
    profit_float = float(profit)
    
    # 负数（亏损）统一归类为小单
    if profit_float < 0:
        return '小单'
    
    # 小单：SGD 100以内（包括0）
    if profit_float <= 100:
        return '小单'
    
    # 小单-中单过渡：SGD 100-200
    elif profit_float < 200:
        return '小单-中单过渡'
    
    # 中单：SGD 200-500
    elif profit_float < 500:
        return '中单'
    
    # 中单-大单过渡：SGD 500-1000
    elif profit_float < 1000:
        return '中单-大单过渡'
    
    # 大单：SGD 1000以上
    else:
        return '大单'


def calculate_profit_distribution(profit):
    """
    根据盈亏金额计算分配结果（包括负数亏损）
    
    参数:
        profit: 盈亏金额（sub_total_pl），负数代表亏损
    
    返回:
        tuple: (操作员利润, 业务员利润, 公司利润)，负数表示亏损分配
    """
    if profit is None:
        profit = Decimal('0')
    
    if not isinstance(profit, Decimal):
        profit = Decimal(str(profit))
    
    # 如果利润为0，不分配
    if profit == 0:
        return (Decimal('0'), Decimal('0'), Decimal('0'))
    
    # 负数（亏损）和正数（盈利）都按照规则计算分配
    # 根据盈亏金额获取分配比例（负数统一使用小单比例）
    operator_ratio, sales_ratio, company_ratio = calculate_profit_ratios(profit)
    
    # 计算分配金额（负数乘以比例仍然是负数，表示亏损分配）
    operator_profit = profit * operator_ratio
    sales_profit = profit * sales_ratio
    company_profit = profit * company_ratio
    
    # 四舍五入到2位小数
    operator_profit = operator_profit.quantize(Decimal('0.01'))
    sales_profit = sales_profit.quantize(Decimal('0.01'))
    company_profit = company_profit.quantize(Decimal('0.01'))
    
    # 处理四舍五入后的误差（确保总和等于原始利润/亏损）
    total_allocated = operator_profit + sales_profit + company_profit
    difference = profit - total_allocated
    
    # 将误差加到公司利润上（或可以根据业务需求调整）
    if abs(difference) > Decimal('0.01'):
        company_profit += difference
    
    return (operator_profit, sales_profit, company_profit)

