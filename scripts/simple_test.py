import pandas as pd

def test_date():
    date_str = "2029/7/25"
    parts = date_str.split('/')
    year_str, month_str, day_str = parts
    
    year = int(year_str)
    actual_year = 2000 + (year % 100)
    
    print(f"原始: {date_str}")
    print(f"年份: {year}")
    print(f"实际年份: {actual_year}")
    print(f"结果: {actual_year}-{int(month_str):02d}-{int(day_str):02d}")

test_date() 