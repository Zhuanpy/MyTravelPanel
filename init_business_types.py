#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化新架构业务类型的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_business_types():
    """初始化业务类型"""
    try:
        from App_new import create_app
        from App_new.exts import db
        from App_new.shared.models.business_types import BusinessType
        
        print("🚀 启动新架构应用...")
        app = create_app()
        
        with app.app_context():
            print("🔍 检查现有业务类型...")
            existing_types = BusinessType.query.all()
            print(f"✓ 找到 {len(existing_types)} 个现有业务类型")
            
            if existing_types:
                print("📋 现有业务类型:")
                for bt in existing_types:
                    print(f"  - {bt.code}: {bt.name}")
            
            print("\n🔧 初始化默认业务类型...")
            BusinessType.init_default_types()
            
            print("\n✅ 验证初始化结果...")
            all_types = BusinessType.query.all()
            print(f"✓ 现在共有 {len(all_types)} 个业务类型")
            
            # 特别检查旅游团类型
            tour_type = BusinessType.query.filter_by(name='旅游团').first()
            if tour_type:
                print(f"✅ 旅游团业务类型已创建: ID={tour_type.id}, Code={tour_type.code}")
            else:
                print("❌ 旅游团业务类型创建失败")
            
            print("\n🏁 业务类型初始化完成！")
            
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = init_business_types()
    if success:
        print("\n🎉 业务类型初始化成功！现在可以创建旅游团REF了。")
    else:
        print("\n💥 业务类型初始化失败，请检查错误信息。")

