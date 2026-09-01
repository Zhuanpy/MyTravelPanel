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
