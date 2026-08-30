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


def calculate_profit_ratios(profit, ratio_basis=None):
    """
    根据盈亏金额计算利润分配比例

    参数:
        profit: 盈亏金额（SGD），负数代表亏损
        ratio_basis: 用来决定档位的金额；不传则用 profit 本身。
            退款/调整单需要传主单的利润：这套规则是按**总利润**分档而不是按增量分档，
            10 块钱单独成单会落到小单档(40/30/30)，并进 2000 的大单则是(20/40/40)，
            同一笔钱分成差一倍。传主单利润可以让调整单沿用主单档位。

    返回:
        tuple: (操作员比例, 业务员比例, 公司比例)
    """
    if profit is None:
        profit = Decimal('0')
    
    # 确保profit是Decimal类型
    if not isinstance(profit, Decimal):
        profit = Decimal(str(profit))

    basis = profit if ratio_basis is None else ratio_basis
    if not isinstance(basis, Decimal):
        basis = Decimal(str(basis))

    profit_float = float(basis)
    
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


def get_order_type(profit, ratio_basis=None):
    """
    根据盈亏金额获取订单类型

    参数:
        profit: 盈亏金额（SGD），负数代表亏损
        ratio_basis: 用来决定档位的金额；不传则用 profit 本身。
            传了就返回该基准对应的档位——调整单沿用主单档位时，
            存的 order_type 要能解释它为什么按这个比例分。

    返回:
        str: 订单类型名称
    """
    if profit is None and ratio_basis is None:
        return None

    basis = profit if ratio_basis is None else ratio_basis
    if basis is None:
        return None
    if not isinstance(basis, Decimal):
        basis = Decimal(str(basis))

    profit_float = float(basis)
    
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


def calculate_profit_distribution(profit, ratio_basis=None):
    """
    根据盈亏金额计算分配结果（包括负数亏损）

    参数:
        profit: 盈亏金额（sub_total_pl），负数代表亏损
        ratio_basis: 用来决定分配比例档位的金额；不传则用 profit 本身。
            金额仍然按 profit 分，只是比例取自 ratio_basis 所在的档位。

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
    operator_ratio, sales_ratio, company_ratio = calculate_profit_ratios(profit, ratio_basis)
    
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


def get_ratio_basis(project):
    """取一个项目做利润分配时应使用的「档位基准金额」

    退款/调整单（related_header_id 指向主单）沿用主单的档位，避免同一笔钱
    因为挂在哪张单上不同而分成差一倍。普通订单返回 None，表示按自身利润分档。

    只向上找一层，不递归：调整单的主单本身不该再是调整单，
    真出现了也当普通单处理，防止环状引用把结算卡死。
    """
    if project is None or not getattr(project, 'related_header_id', None):
        return None
    if project.related_header_id == project.id:
        return None  # 自己指自己，忽略

    from App_new.business.projects.models.project import ProjectHeader
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.exts import db

    main = ProjectHeader.query.get(project.related_header_id)
    if main is None:
        return None

    row = db.session.query(
        db.func.coalesce(db.func.sum(ProjectRef.selling_price), 0),
        db.func.coalesce(db.func.sum(ProjectRef.cost_price), 0)
    ).filter(ProjectRef.header_id == main.id).one()
    return Decimal(str(row[0] or 0)) - Decimal(str(row[1] or 0))


def apply_profit_distribution(project):
    """按项目当前的 REF 重算利润分配并写回项目，返回 (利润, 操作员, 业务员, 公司)

    结算必须调用它，不能直接读 project.operator_profit：
    那三个字段是「计算利润分配」按钮留下的快照，而结算单里的 total_profit
    是实时从 REF 算的。两者不是同一次计算的结果——没点过按钮就结算，分成按 0
    入账；REF 价格改过再结算，分成还是旧数字。库里已经因此出现过
    「结算单利润 3008.50 / 分成合计 0.00」和「分成比利润多分 319.80」。

    调用方负责 commit。
    """
    from App_new.business.projects.models.ref import ProjectRef
    from App_new.exts import db

    row = db.session.query(
        db.func.coalesce(db.func.sum(ProjectRef.selling_price), 0),
        db.func.coalesce(db.func.sum(ProjectRef.cost_price), 0)
    ).filter(ProjectRef.header_id == project.id).one()
    profit = Decimal(str(row[0] or 0)) - Decimal(str(row[1] or 0))

    # 退款/调整单沿用主单档位
    basis = get_ratio_basis(project)
    project.order_type = get_order_type(profit, basis)

    if profit == 0:
        operator = sales = company = Decimal('0')
    else:
        operator, sales, company = calculate_profit_distribution(profit, basis)

    project.operator_profit = operator
    project.sales_profit = sales
    project.company_profit = company
    return profit, operator, sales, company
