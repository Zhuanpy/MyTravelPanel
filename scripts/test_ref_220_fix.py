#!/usr/bin/env python3
"""
测试REF 220的修复效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectRef
import json

def test_ref_220_fix():
    """测试REF 220的修复效果"""
    app = create_app()
    
    with app.app_context():
        try:
            print("测试REF 220的修复效果...")
            
            # 获取REF 220
            ref = ProjectRef.query.get(220)
            if not ref:
                print("❌ REF 220不存在")
                return
            
            # 解析extra_info
            if ref.extra_info:
                visa_info = json.loads(ref.extra_info)
                
                print("当前extra_info数据结构:")
                for key, value in visa_info.items():
                    print(f"  {key}: {value}")
                
                # 检查字段名兼容性
                print("\n字段名兼容性检查:")
                country_old = visa_info.get('country', '')
                country_new = visa_info.get('visa_country', '')
                visa_type = visa_info.get('visa_type', '')
                
                print(f"  旧字段名 'country': '{country_old}'")
                print(f"  新字段名 'visa_country': '{country_new}'")
                print(f"  签证类型 'visa_type': '{visa_type}'")
                
                # 确定应该使用的国家值
                country_to_use = country_old if country_old else country_new
                print(f"  应该使用的国家值: '{country_to_use}'")
                
                if country_to_use:
                    print("  ✅ 国家字段有值，应该能正常填充")
                else:
                    print("  ❌ 国家字段为空")
                
                if visa_type:
                    print("  ✅ 签证类型字段有值，应该能正常填充")
                else:
                    print("  ❌ 签证类型字段为空")
                
                # 检查是否需要更新数据结构
                print("\n数据结构更新建议:")
                if not country_old and country_new:
                    print("  ⚠️ 建议将 'visa_country' 的值复制到 'country' 字段")
                    print("  这样可以确保向后兼容性")
                    
                    # 更新数据结构
                    visa_info['country'] = country_new
                    ref.extra_info = json.dumps(visa_info, ensure_ascii=False)
                    db.session.commit()
                    print("  ✅ 已更新数据结构，添加了 'country' 字段")
                
            else:
                print("❌ extra_info字段为空")
            
            print("\n✅ REF 220修复测试完成")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_ref_220_fix() 