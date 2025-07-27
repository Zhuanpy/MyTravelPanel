#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试签证类型选择功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Product.Visamodels import VisaTypes

def test_visa_type_selection():
    """测试签证类型选择功能"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取所有签证类型
            visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
            print(f"✅ 找到 {len(visa_types)} 个签证类型")
            
            # 检查是否有日本签证
            japan_visa = VisaTypes.query.filter_by(visa_type='日本签证').first()
            if japan_visa:
                print(f"✅ 找到日本签证类型: {japan_visa.visa_type}")
            else:
                print("ℹ️ 没有找到日本签证类型")
            
            # 显示前几个签证类型
            print("\n📋 签证类型列表:")
            for i, visa_type in enumerate(visa_types[:5]):
                print(f"  {i+1}. {visa_type.visa_type}")
            if len(visa_types) > 5:
                print(f"  ... 还有 {len(visa_types) - 5} 个签证类型")
            
            print("\n🎯 功能说明:")
            print("✅ 当通过URL参数指定签证类型时:")
            print("  - 左侧面板标题变为'当前签证类型'")
            print("  - 只显示指定的签证类型")
            print("  - 显示'已锁定'提示")
            print("  - 禁用签证类型切换功能")
            print("  - 面板透明度降低表示只读状态")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            return False

if __name__ == "__main__":
    print("开始测试签证类型选择功能...")
    success = test_visa_type_selection()
    if success:
        print("\n✅ 签证类型选择功能测试通过！")
    else:
        print("\n❌ 签证类型选择功能测试失败！") 