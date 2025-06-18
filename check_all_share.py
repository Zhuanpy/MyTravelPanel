import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Visamodels import db

app = create_app()

with app.app_context():
    # 直接执行SQL查询
    result = db.session.execute("""
        SELECT id, visa_type_id, singapore_identity_id, additional_info, created_at
        FROM visa_documents_request 
        WHERE visa_type_id = 2
        ORDER BY id
    """).fetchall()
    
    print("日本签证(visa_type_id=2)的所有记录:")
    print("=" * 80)
    
    for row in result:
        print(f"ID: {row[0]}")
        print(f"签证类型ID: {row[1]}")
        print(f"身份ID: {row[2]}")
        print(f"补充信息: {row[3]}")
        print(f"创建时间: {row[4]}")
        print("-" * 40)
    
    # 特别查看id=9的记录
    result_9 = db.session.execute("""
        SELECT id, visa_type_id, singapore_identity_id, additional_info
        FROM visa_documents_request 
        WHERE id = 9
    """).fetchall()
    
    if result_9:
        print("\nID=9的记录详情:")
        print("=" * 40)
        row = result_9[0]
        print(f"ID: {row[0]}")
        print(f"签证类型ID: {row[1]}")
        print(f"身份ID: {row[2]}")
        print(f"补充信息: {row[3]}")
        
        # 检查这个记录是否属于日本签证
        if row[1] == 2:
            print("✓ 这个记录属于日本签证")
        else:
            print(f"✗ 这个记录不属于日本签证，属于签证类型ID: {row[1]}")
    else:
        print("\n没有找到ID=9的记录") 