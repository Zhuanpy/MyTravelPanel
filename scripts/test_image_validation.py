#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图片文件验证
"""

import os
from PIL import Image

def test_image_file(image_path):
    """测试单个图片文件"""
    print(f"测试图片: {image_path}")
    
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print("  ✗ 文件不存在")
            return False
        
        # 检查文件大小
        file_size = os.path.getsize(image_path)
        print(f"  文件大小: {file_size} 字节")
        
        if file_size == 0:
            print("  ✗ 文件为空")
            return False
        
        # 尝试打开图片
        with Image.open(image_path) as img:
            print(f"  图片格式: {img.format}")
            print(f"  图片模式: {img.mode}")
            print(f"  图片尺寸: {img.size}")
            
            # 验证图片
            try:
                img.verify()
                print("  ✓ 图片验证通过")
            except Exception as verify_error:
                print(f"  ✗ 图片验证失败: {verify_error}")
                return False
            
            # 尝试转换为RGB
            try:
                if img.mode != 'RGB':
                    rgb_img = img.convert('RGB')
                    print("  ✓ RGB转换成功")
                else:
                    print("  ✓ 已经是RGB模式")
            except Exception as convert_error:
                print(f"  ✗ RGB转换失败: {convert_error}")
                return False
        
        print("  ✓ 图片文件有效")
        return True
        
    except Exception as e:
        print(f"  ✗ 处理图片时出错: {e}")
        return False

def main():
    """主函数"""
    # 测试您提到的图片文件
    test_path = r"E:\Todays file\111\未标题-1.jpg"
    
    print("=== 图片文件验证测试 ===")
    
    if test_image_file(test_path):
        print("\n✅ 图片文件验证通过，可以正常处理")
    else:
        print("\n❌ 图片文件有问题，需要检查")
    
    # 如果测试文件夹存在，测试文件夹中的所有图片
    folder_path = r"E:\Todays file\111"
    if os.path.exists(folder_path):
        print(f"\n=== 测试文件夹: {folder_path} ===")
        
        image_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                image_files.append(os.path.join(folder_path, file))
        
        print(f"找到 {len(image_files)} 个图片文件")
        
        valid_count = 0
        for img_path in image_files:
            if test_image_file(img_path):
                valid_count += 1
            print()
        
        print(f"有效图片: {valid_count}/{len(image_files)}")

if __name__ == "__main__":
    main() 