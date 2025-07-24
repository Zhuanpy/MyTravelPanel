#!/usr/bin/env python3
"""
测试签证类型API接口
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_visa_api():
    """测试签证类型API接口"""
    from App import create_app
    from App.models.Product.Visamodels import VisaCountries, VisaTypes
    
    app = create_app()
    with app.app_context():
        print("=== 测试签证类型API接口 ===")
        
        # 获取所有国家
        countries = VisaCountries.query.all()
        print(f"找到 {len(countries)} 个国家:")
        for country in countries:
            print(f"  - {country.country_name_CN} (ID: {country.id})")
            
            # 获取该国家的签证类型
            visa_types = VisaTypes.query.filter_by(country_id=country.id).all()
            print(f"    签证类型数量: {len(visa_types)}")
            for vt in visa_types:
                print(f"      - {vt.visa_type} (处理时间: {vt.processing_time}, 费用: {vt.fee})")
            print()

if __name__ == "__main__":
    test_visa_api() 