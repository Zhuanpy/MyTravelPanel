#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试长截图切分功能
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from App.code.utils.screenshot_splitter import ScreenshotSplitter

def test_screenshot_splitter():
    """测试长截图切分功能"""
    
    # 测试文件夹路径（请根据实际情况修改）
    test_folder = r"E:\Todays file\111"
    
    if not os.path.exists(test_folder):
        print(f"测试文件夹不存在: {test_folder}")
        return
    
    try:
        print("开始测试长截图切分功能...")
        print(f"测试文件夹: {test_folder}")
        
        # 创建切分器实例
        splitter = ScreenshotSplitter(test_folder, margin_size_mm=20)
        
        # 处理长截图
        result = splitter.process_screenshots()
        
        print("测试结果:")
        print(f"成功: {result['success']}")
        print(f"处理文件数: {result['files_processed']}")
        print(f"总页数: {result['pages']}")
        print("详细信息:")
        for detail in result['details']:
            print(f"  - {detail['file']}: {detail['pages']} 页")
        
        print("测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_screenshot_splitter() 