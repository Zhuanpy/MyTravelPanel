# -*- coding: utf-8 -*-
"""
REF extra_info 公共解析

各业务类型的 REF 把"出发/开始日期"存进 extra_info 时用了各自的键名
（酒店 checkin_date、保险 start_date、景点 visit_date、其他 service_date……），
下游的发票、对账单、SOA 如果只认某一个键，就会出现日期空白。
这里统一口径，各处调用同一套解析逻辑。

机票的日期来自 project_flight_segments 表，不走 extra_info，由调用方自行处理。
"""

# "出发/开始日期"在 extra_info 里可能的键名，按优先级排列
REF_START_DATE_KEYS = (
    'departure_date',   # 团队 / 交通 / 签证；酒店也冗余存了一份(=checkin_date)
    'checkin_date',     # 酒店
    'start_date',       # 保险（保单生效日）
    'visit_date',       # 景点 / 门票
    'service_date',     # 其他
)


def resolve_ref_start_date(extra_data):
    """从 extra_info 字典里取"出发/开始日期"，取不到返回空字符串"""
    if not isinstance(extra_data, dict):
        return ''
    for key in REF_START_DATE_KEYS:
        value = extra_data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def normalize_ref_dates(extra_data):
    """把各业务类型的日期补写成统一的 departure_date

    模板里"其他类型通用显示"分支只读 departure_date，保险/景点/其他这几类
    原本没有这个键，Date 一行就整行不显示。这里就地补上并返回同一个字典。
    """
    if not isinstance(extra_data, dict):
        return extra_data

    current = extra_data.get('departure_date')
    if current is None or not str(current).strip():
        resolved = resolve_ref_start_date(extra_data)
        if resolved:
            extra_data['departure_date'] = resolved

    return extra_data


def fill_hotel_nights(extra_data):
    """补算酒店晚数

    现在的酒店表单会把 nights 一起存进 extra_info，但早期表单只存了
    入住/退房日期，发票上就没法显示"几晚"。这里在缺失时用日期补算。
    """
    if not isinstance(extra_data, dict):
        return extra_data

    checkin = extra_data.get('checkin_date')
    checkout = extra_data.get('checkout_date')
    if not checkin or not checkout:
        return extra_data

    try:
        nights = int(extra_data.get('nights') or 0)
    except (TypeError, ValueError):
        nights = 0
    if nights > 0:
        return extra_data

    from datetime import datetime
    try:
        start = datetime.strptime(str(checkin).strip()[:10], '%Y-%m-%d').date()
        end = datetime.strptime(str(checkout).strip()[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return extra_data

    delta = (end - start).days
    if delta > 0:
        extra_data['nights'] = delta

    return extra_data


def enrich_ref_extra_data(extra_data):
    """发票/对账单渲染前对 extra_info 做的统一补全

    路由里的 build_ref_extra_data 都调这一个入口，避免各处逻辑再次分叉。
    """
    normalize_ref_dates(extra_data)
    fill_hotel_nights(extra_data)
    return extra_data
