#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCBC页面响应式设计
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_responsive_design():
    """测试响应式设计功能"""
    
    print("=== OCBC页面响应式设计测试 ===")
    
    print("响应式断点：")
    print("  - 大屏幕：≥1200px - 显示左侧导航")
    print("  - 中屏幕：768px-1199px - 隐藏左侧导航，调整布局")
    print("  - 小屏幕：<768px - 隐藏左侧导航，隐藏部分列，优化布局")
    
    print("\nCSS媒体查询：")
    print("  @media (max-width: 1199px) {")
    print("    .sidebar { display: none !important; }")
    print("    .main-content { margin-left: 0 !important; width: 100% !important; }")
    print("  }")
    
    print("\nJavaScript响应式处理：")
    print("  - 监听窗口大小变化 (resize)")
    print("  - 监听窗口最大化/还原 (maximize/restore)")
    print("  - 动态调整侧边栏显示/隐藏")
    print("  - 动态调整主内容区域布局")
    
    print("\n小屏幕优化：")
    print("  - 隐藏记账日期列")
    print("  - 隐藏REF/EO列")
    print("  - 调整字体大小")
    print("  - 优化表格间距")
    print("  - 筛选表单垂直排列")
    
    print("\n测试步骤：")
    print("1. 访问OCBC页面：http://127.0.0.1:5000/statement/ocbc_bank")
    print("2. 调整浏览器窗口宽度到1200px以下")
    print("3. 检查左侧导航是否隐藏")
    print("4. 检查主内容区域是否占满全宽")
    print("5. 调整窗口宽度到768px以下")
    print("6. 检查表格列是否隐藏和调整")
    print("7. 恢复窗口大小，检查布局是否恢复")

if __name__ == '__main__':
    test_responsive_design()

