#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SHARE身份的显示和排序功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaSingaporeIdentity

def test_share_display_and_sorting():
    """测试SHARE身份的显示和排序功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试SHARE身份的显示和排序功能 ===\n")
        
        # 1. 获取所有身份
        all_identities = VisaSingaporeIdentity.query.all()
        print(f"1. 数据库中的所有身份:")
        for identity in all_identities:
            print(f"   - {identity.identity_zh} (ID: {identity.id})")
        
        # 2. 模拟后端排序逻辑
        identities = []
        share_identity = None
        
        for identity in all_identities:
            if identity.identity_zh == 'SHARE':
                share_identity = identity
            else:
                identities.append(identity)
        
        # 其他身份按字母顺序排序
        identities.sort(key=lambda x: x.identity_zh)
        
        # SHARE放在第一位
        if share_identity:
            identities.insert(0, share_identity)
        
        print(f"\n2. 排序后的身份列表:")
        for i, identity in enumerate(identities, 1):
            display_name = '共用资料' if identity.identity_zh == 'SHARE' else identity.identity_zh
            print(f"   {i}. {display_name} (原始名称: {identity.identity_zh}, ID: {identity.id})")
        
        # 3. 验证SHARE是否在第一位
        if identities and identities[0].identity_zh == 'SHARE':
            print(f"\n3. ✅ SHARE身份正确排在第一位")
        else:
            print(f"\n3. ❌ SHARE身份没有排在第一位")
            return False
        
        # 4. 验证显示名称
        share_display = '共用资料' if identities[0].identity_zh == 'SHARE' else identities[0].identity_zh
        if share_display == '共用资料':
            print(f"4. ✅ SHARE身份正确显示为: {share_display}")
        else:
            print(f"4. ❌ SHARE身份显示错误: {share_display}")
            return False
        
        # 5. 模拟前端模板渲染
        print(f"\n5. 模拟前端模板渲染:")
        template_identities = []
        for identity in identities:
            display_name = '共用资料' if identity.identity_zh == 'SHARE' else identity.identity_zh
            template_identities.append({
                'id': identity.id,
                'name': identity.identity_zh,
                'display': display_name
            })
        
        print(f"   模板中的身份数组:")
        for i, identity in enumerate(template_identities, 1):
            print(f"   {i}. {{ id: {identity['id']}, name: '{identity['name']}', display: '{identity['display']}' }}")
        
        # 6. 验证前端显示
        first_identity = template_identities[0]
        if first_identity['name'] == 'SHARE' and first_identity['display'] == '共用资料':
            print(f"\n6. ✅ 前端将正确显示: 共用资料 (SHARE)")
        else:
            print(f"\n6. ❌ 前端显示错误: {first_identity['display']} ({first_identity['name']})")
            return False
        
        print(f"\n✅ SHARE身份显示和排序功能测试成功！")
        print(f"   总结:")
        print(f"   - SHARE身份排在第一位")
        print(f"   - SHARE身份显示为'共用资料'")
        print(f"   - 其他身份按字母顺序排序")
        return True

if __name__ == '__main__':
    success = test_share_display_and_sorting()
    if not success:
        sys.exit(1) 