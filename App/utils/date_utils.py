from datetime import datetime, timedelta

def get_date_by_day_delta(days: int = 0) -> str:
    """
    获取指定天数偏移的日期，格式为YYYY-MM-DD
    
    参数:
        days: 相对于今天的天数偏移量，可正可负
        
    返回:
        格式化的日期字符串，例如：2025-05-10
    """
    target_date = datetime.now() + timedelta(days=days)
    return target_date.strftime('%Y-%m-%d') 