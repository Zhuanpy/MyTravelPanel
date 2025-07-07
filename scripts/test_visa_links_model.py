#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试VisaLinks模型的新字段
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.Visamodels import VisaLinks, VisaCountries, VisaTypes

def test_visa_links_model():
    """测试VisaLinks模型的新字段"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试VisaLinks模型的新字段 ===")
        
        try:
            # 1. 检查表结构
            print("1. 检查表结构...")
            
            # 获取所有国家
            countries = VisaCountries.query.all()
            print(f"   ✓ 找到 {len(countries)} 个国家")
            
            # 获取所有签证类型
            visa_types = VisaTypes.query.all()
            print(f"   ✓ 找到 {len(visa_types)} 个签证类型")
            
            # 获取所有链接
            links = VisaLinks.query.all()
            print(f"   ✓ 找到 {len(links)} 个链接")
            
            # 2. 测试新字段
            print("\n2. 测试新字段...")
            
            for link in links[:5]:  # 只显示前5个
                print(f"   链接ID: {link.id}")
                print(f"   名称: {link.name}")
                print(f"   visa_type_id: {link.visa_type_id}")
                print(f"   visa_countries_id: {link.visa_countries_id}")
                
                # 测试关系
                if link.country:
                    print(f"   国家名称: {link.country.country_name_CN}")
                else:
                    print(f"   国家名称: 未设置")
                    
                if link.visa_type:
                    print(f"   签证类型: {link.visa_type.visa_type}")
                else:
                    print(f"   签证类型: 未设置")
                    
                print("   ---")
            
            # 3. 测试to_dict方法
            print("\n3. 测试to_dict方法...")
            if links:
                link_dict = links[0].to_dict()
                print(f"   字典键: {list(link_dict.keys())}")
                if 'visa_countries_id' in link_dict:
                    print("   ✓ visa_countries_id 字段存在")
                else:
                    print("   ✗ visa_countries_id 字段不存在")
                    
                if 'country_name' in link_dict:
                    print("   ✓ country_name 字段存在")
                else:
                    print("   ✗ country_name 字段不存在")
            
            # 4. 测试查询
            print("\n4. 测试查询...")
            
            # 按国家查询
            if countries:
                country_id = countries[0].id
                country_links = VisaLinks.query.filter_by(visa_countries_id=country_id).all()
                print(f"   国家ID {country_id} 的链接数量: {len(country_links)}")
            
            # 5. 测试创建新记录
            print("\n5. 测试创建新记录...")
            
            if countries and visa_types:
                # 创建测试链接
                test_link = VisaLinks(
                    visa_type_id=visa_types[0].id,
                    visa_countries_id=countries[0].id,
                    name="测试链接",
                    link="https://test.com"
                )
                
                print(f"   创建测试链接: {test_link.name}")
                print(f"   签证类型ID: {test_link.visa_type_id}")
                print(f"   国家ID: {test_link.visa_countries_id}")
                
                # 注意：这里只是测试，不实际保存到数据库
                print("   ✓ 模型创建成功")
            
            print("\n✅ VisaLinks模型测试完成！")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_visa_links_model() 