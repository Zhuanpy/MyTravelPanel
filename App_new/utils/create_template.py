import pandas as pd
import os

def create_account_template():
    # 定义模板数据
    template_data = {
        'platform': ['示例：携程', '示例：booking'],
        'username': ['example@email.com', 'username123'],
        'password': ['password123', 'pass456'],
        'category': ['机票', '酒店'],
        'website_url': ['https://www.ctrip.com', 'https://www.booking.com'],
        'owner': ['市场部', '运营部'],
        'country': ['中国', '新加坡'],
        'region': ['上海', '新加坡'],
        'description': ['携程商旅账号', '酒店预订账号'],
        'notes': ['主要用于机票预订', '用于东南亚酒店预订']
    }

    # 创建DataFrame
    df = pd.DataFrame(template_data)

    # 确保目标目录存在
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    # 保存模板
    template_path = os.path.join(template_dir, 'account_template.xlsx')
    
    # 创建Excel写入器
    with pd.ExcelWriter(template_path, engine='openpyxl') as writer:
        # 写入数据
        df.to_excel(writer, index=False, sheet_name='账号数据')
        
        # 获取工作表
        worksheet = writer.sheets['账号数据']
        
        # 设置列宽
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

    print(f"模板已创建: {template_path}")

if __name__ == '__main__':
    create_account_template() 