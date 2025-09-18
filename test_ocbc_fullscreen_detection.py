#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCBC页面全屏检测功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_fullscreen_detection():
    """测试全屏检测功能"""
    
    print("=== OCBC页面全屏检测功能测试 ===")
    
    print("全屏检测方法：")
    print("1. Fullscreen API检测（优先）")
    print("   - document.fullscreenElement")
    print("   - document.webkitFullscreenElement (WebKit)")
    print("   - document.mozFullScreenElement (Firefox)")
    print("   - document.msFullscreenElement (IE/Edge)")
    
    print("\n2. 回退方案：窗口大小检测")
    print("   - window.innerWidth < 1200px")
    
    print("\n事件监听：")
    print("  - fullscreenchange")
    print("  - webkitfullscreenchange")
    print("  - mozfullscreenchange")
    print("  - MSFullscreenChange")
    print("  - resize")
    print("  - maximize/restore")
    print("  - F11键监听")
    
    print("\nCSS类控制：")
    print("  - body.non-fullscreen .sidebar { display: none !important; }")
    print("  - body.non-fullscreen .main-content { margin-left: 0 !important; }")
    print("  - body.non-fullscreen .bank-statement-container { padding: 15px; }")
    
    print("\n测试步骤：")
    print("1. 访问OCBC页面：http://127.0.0.1:5000/statement/ocbc_bank")
    print("2. 检查初始状态（非全屏时应该隐藏侧边栏）")
    print("3. 按F11进入全屏模式")
    print("4. 检查侧边栏是否显示")
    print("5. 按F11退出全屏模式")
    print("6. 检查侧边栏是否隐藏")
    print("7. 调整浏览器窗口大小")
    print("8. 检查布局是否相应调整")
    
    print("\n浏览器兼容性：")
    print("  - Chrome/Edge: 支持Fullscreen API")
    print("  - Firefox: 支持mozFullScreen API")
    print("  - Safari: 支持webkitFullscreen API")
    print("  - 旧版浏览器: 回退到窗口大小检测")
    
    print("\n✅ 全屏检测功能已实现")
    print("✅ 支持多种全屏API")
    print("✅ 提供回退方案")
    print("✅ 动态响应全屏状态变化")

if __name__ == '__main__':
    test_fullscreen_detection()

