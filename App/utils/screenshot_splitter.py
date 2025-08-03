#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长截图切分工具
将长截图按A4纸张比例切分，并合并成PDF便于打印
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont
import tempfile
from PyPDF2 import PdfMerger


class ScreenshotSplitter:
    def __init__(self, folder_path, margin_size_mm=20):
        """
        初始化长截图切分器
        
        Args:
            folder_path (str): 包含长截图的文件夹路径
            margin_size_mm (int): 上下边距大小（毫米）
        """
        self.folder_path = folder_path
        self.margin_size_mm = margin_size_mm
        
        # A4纸张尺寸（像素，300DPI）
        self.a4_width_px = 2480  # A4宽度 210mm * 300DPI / 25.4
        self.a4_height_px = 3508  # A4高度 297mm * 300DPI / 25.4
        
        # 边距转换（毫米转像素）
        self.margin_px = int(margin_size_mm * 300 / 25.4)
        
        # 实际可用高度（减去上下边距）
        self.usable_height = self.a4_height_px - (2 * self.margin_px)
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    def process_screenshots(self):
        """
        处理文件夹中的所有长截图
        
        Returns:
            dict: 处理结果信息
        """
        try:
            # 获取所有图片文件
            image_files = self._get_image_files()
            if not image_files:
                raise ValueError("文件夹中没有找到支持的图片文件")
            
            total_pages = 0
            processed_files = []
            
            # 处理每个图片文件
            for image_file in image_files:
                file_path = os.path.join(self.folder_path, image_file)
                pages = self._split_single_image(file_path)
                total_pages += pages
                processed_files.append({
                    'file': image_file,
                    'pages': pages
                })
            
            # 合并所有PDF文件
            self._merge_pdfs()
            
            return {
                'success': True,
                'files_processed': len(processed_files),
                'pages': total_pages,
                'details': processed_files
            }
            
        except Exception as e:
            raise Exception(f"处理长截图时发生错误: {str(e)}")
    
    def _get_image_files(self):
        """获取文件夹中的图片文件列表"""
        image_files = []
        for file in os.listdir(self.folder_path):
            if os.path.isfile(os.path.join(self.folder_path, file)):
                ext = os.path.splitext(file)[1].lower()
                if ext in self.supported_formats:
                    image_files.append(file)
        
        # 按文件名排序
        image_files.sort()
        return image_files
    
    def _split_single_image(self, image_path):
        """
        切分单个长截图
        
        Args:
            image_path (str): 图片文件路径
            
        Returns:
            int: 生成的页数
        """
        try:
            # 验证图片文件
            if not os.path.exists(image_path):
                raise Exception(f"图片文件不存在: {image_path}")
            
            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                raise Exception(f"图片文件为空: {image_path}")
            
            # 打开图片并验证
            try:
                with Image.open(image_path) as img:
                    # 验证图片是否有效
                    img.verify()
            except Exception as verify_error:
                raise Exception(f"图片文件损坏或格式不支持: {image_path}, 错误: {str(verify_error)}")
            
            # 重新打开图片进行处理
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                width, height = img.size
                
                # 验证图片尺寸
                if width <= 0 or height <= 0:
                    raise Exception(f"图片尺寸无效: {width}x{height}")
                
                # 计算需要切分的页数
                pages_needed = math.ceil(height / self.usable_height)
                
                if pages_needed <= 0:
                    raise Exception(f"计算页数失败: {pages_needed}")
                
                # 创建临时文件夹存储切分后的图片
                temp_dir = tempfile.mkdtemp()
                split_images = []
                
                try:
                    # 切分图片
                    for page in range(pages_needed):
                        # 计算当前页的起始和结束位置
                        start_y = page * self.usable_height
                        end_y = min(start_y + self.usable_height, height)
                        
                        # 创建A4尺寸的白色背景
                        page_image = Image.new('RGB', (self.a4_width_px, self.a4_height_px), 'white')
                        
                        # 计算图片在页面中的位置（居中）
                        img_width = width
                        img_height = end_y - start_y
                        
                        # 如果图片宽度超过A4宽度，按比例缩放
                        if img_width > self.a4_width_px:
                            scale = self.a4_width_px / img_width
                            img_width = self.a4_width_px
                            img_height = int(img_height * scale)
                        
                        # 裁剪原图的一部分
                        cropped = img.crop((0, start_y, width, end_y))
                        
                        # 如果需要缩放
                        if img_width != width:
                            cropped = cropped.resize((img_width, img_height), Image.Resampling.LANCZOS)
                        
                        # 计算居中位置
                        x_offset = (self.a4_width_px - img_width) // 2
                        y_offset = self.margin_px
                        
                        # 将裁剪的图片粘贴到A4背景上
                        page_image.paste(cropped, (x_offset, y_offset))
                        
                        # 保存切分后的图片
                        output_path = os.path.join(temp_dir, f'page_{page + 1:03d}.jpg')
                        page_image.save(output_path, 'JPEG', quality=95)
                        split_images.append(output_path)
                    
                    # 验证切分后的图片
                    if not split_images:
                        raise Exception("没有生成切分后的图片")
                    
                    # 将切分后的图片合并为PDF
                    pdf_path = os.path.join(self.folder_path, f'{os.path.splitext(os.path.basename(image_path))[0]}_split.pdf')
                    self._images_to_pdf(split_images, pdf_path)
                    
                    return pages_needed
                    
                finally:
                    # 清理临时文件
                    for temp_file in split_images:
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except:
                                pass  # 忽略删除错误
                    try:
                        os.rmdir(temp_dir)
                    except:
                        pass  # 忽略删除错误
                
        except Exception as e:
            raise Exception(f"切分图片 {image_path} 时发生错误: {str(e)}")
    
    def _images_to_pdf(self, image_paths, output_pdf_path):
        """
        将图片列表合并为PDF
        
        Args:
            image_paths (list): 图片文件路径列表
            output_pdf_path (str): 输出PDF文件路径
        """
        try:
            if not image_paths:
                raise Exception("没有图片文件可以处理")
            
            # 验证所有图片文件
            valid_images = []
            for img_path in image_paths:
                if not os.path.exists(img_path):
                    print(f"警告: 图片文件不存在: {img_path}")
                    continue
                
                try:
                    with Image.open(img_path) as img:
                        # 验证图片
                        img.verify()
                        valid_images.append(img_path)
                except Exception as img_error:
                    print(f"警告: 图片文件损坏: {img_path}, 错误: {str(img_error)}")
                    continue
            
            if not valid_images:
                raise Exception("没有有效的图片文件可以处理")
            
            # 使用第一张有效图片作为基础
            with Image.open(valid_images[0]) as first_image:
                if first_image.mode != 'RGB':
                    first_image = first_image.convert('RGB')
                
                # 准备其他图片
                other_images = []
                for img_path in valid_images[1:]:
                    try:
                        with Image.open(img_path) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            other_images.append(img)
                    except Exception as img_error:
                        print(f"警告: 处理图片时出错: {img_path}, 错误: {str(img_error)}")
                        continue
                
                # 保存为PDF - 使用更简单的方法
                try:
                    print(f"开始生成PDF，图片数量: {len(valid_images)}")
                    
                    # 先尝试直接保存第一张图片为PDF
                    if len(valid_images) == 1:
                        print("单张图片，直接保存为PDF")
                        first_image.save(output_pdf_path, 'PDF', resolution=300.0)
                    else:
                        # 多张图片时，使用save_all参数
                        print("多张图片，使用save_all参数")
                        first_image.save(
                            output_pdf_path,
                            'PDF',
                            save_all=True,
                            append_images=other_images,
                            resolution=300.0
                        )
                    print(f"PDF生成成功: {output_pdf_path}")
                except Exception as save_error:
                    print(f"PDF保存失败，尝试备用方法: {str(save_error)}")
                    # 备用方法：先保存为图片，再转换为PDF
                    try:
                        self._save_as_images_then_pdf(valid_images, output_pdf_path)
                        print(f"PDF生成成功（备用方法）: {output_pdf_path}")
                    except Exception as backup_error:
                        print(f"备用方法失败: {str(backup_error)}")
                        # 最后尝试：直接使用reportlab
                        try:
                            self._create_pdf_with_reportlab(valid_images, output_pdf_path)
                            print(f"PDF生成成功（reportlab方法）: {output_pdf_path}")
                        except Exception as reportlab_error:
                            raise Exception(f"所有PDF生成方法都失败: {str(reportlab_error)}")
                
        except Exception as e:
            raise Exception(f"生成PDF时发生错误: {str(e)}")
    
    def _save_as_images_then_pdf(self, image_paths, output_pdf_path):
        """
        备用方法：先将图片保存为临时文件，再合并为PDF
        
        Args:
            image_paths (list): 图片文件路径列表
            output_pdf_path (str): 输出PDF文件路径
        """
        try:
            import tempfile
            import shutil
            
            # 创建临时文件夹
            temp_dir = tempfile.mkdtemp()
            temp_images = []
            
            try:
                # 将图片复制到临时文件夹
                for i, img_path in enumerate(image_paths):
                    temp_img_path = os.path.join(temp_dir, f'temp_{i:03d}.jpg')
                    shutil.copy2(img_path, temp_img_path)
                    temp_images.append(temp_img_path)
                
                # 使用reportlab创建PDF
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.utils import ImageReader
                
                # 创建PDF
                c = canvas.Canvas(output_pdf_path, pagesize=A4)
                
                for img_path in temp_images:
                    # 获取图片尺寸
                    with Image.open(img_path) as img:
                        img_width, img_height = img.size
                    
                    # 计算在A4页面上的位置和尺寸
                    page_width, page_height = A4
                    scale = min(page_width / img_width, page_height / img_height) * 0.9  # 留10%边距
                    
                    new_width = img_width * scale
                    new_height = img_height * scale
                    
                    # 居中显示
                    x = (page_width - new_width) / 2
                    y = (page_height - new_height) / 2
                    
                    # 添加图片到PDF
                    c.drawImage(img_path, x, y, width=new_width, height=new_height)
                    c.showPage()
                
                c.save()
                
            finally:
                # 清理临时文件
                for temp_img in temp_images:
                    if os.path.exists(temp_img):
                        try:
                            os.remove(temp_img)
                        except:
                            pass
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                    
        except Exception as e:
            raise Exception(f"备用PDF生成方法失败: {str(e)}")
    
    def _create_pdf_with_reportlab(self, image_paths, output_pdf_path):
        """
        直接使用reportlab创建PDF
        
        Args:
            image_paths (list): 图片文件路径列表
            output_pdf_path (str): 输出PDF文件路径
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            print(f"使用reportlab创建PDF，图片数量: {len(image_paths)}")
            
            # 创建PDF
            c = canvas.Canvas(output_pdf_path, pagesize=A4)
            
            for i, img_path in enumerate(image_paths):
                print(f"处理第 {i+1} 张图片: {img_path}")
                
                # 获取图片尺寸
                with Image.open(img_path) as img:
                    img_width, img_height = img.size
                    print(f"图片尺寸: {img_width} x {img_height}")
                
                # 计算在A4页面上的位置和尺寸
                page_width, page_height = A4
                scale = min(page_width / img_width, page_height / img_height) * 0.9  # 留10%边距
                
                new_width = img_width * scale
                new_height = img_height * scale
                
                # 居中显示
                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2
                
                print(f"PDF页面尺寸: {page_width} x {page_height}")
                print(f"缩放比例: {scale}")
                print(f"新尺寸: {new_width} x {new_height}")
                print(f"位置: ({x}, {y})")
                
                # 添加图片到PDF
                c.drawImage(img_path, x, y, width=new_width, height=new_height)
                c.showPage()
            
            c.save()
            print("reportlab PDF创建完成")
            
        except Exception as e:
            raise Exception(f"reportlab PDF创建失败: {str(e)}")
    
    def _merge_pdfs(self):
        """合并文件夹中的所有PDF文件"""
        try:
            # 获取所有PDF文件
            pdf_files = [f for f in os.listdir(self.folder_path) if f.endswith('.pdf')]
            if len(pdf_files) <= 1:
                return  # 只有一个或没有PDF文件，不需要合并
            
            # 按文件名排序
            pdf_files.sort()
            
            # 合并PDF
            merger = PdfMerger()
            for pdf_file in pdf_files:
                pdf_path = os.path.join(self.folder_path, pdf_file)
                merger.append(pdf_path)
            
            # 保存合并后的PDF
            output_path = os.path.join(self.folder_path, 'merged_screenshots.pdf')
            merger.write(output_path)
            merger.close()
            
            # 删除单个PDF文件（可选，保留注释）
            # for pdf_file in pdf_files:
            #     pdf_path = os.path.join(self.folder_path, pdf_file)
            #     os.remove(pdf_path)
            
        except Exception as e:
            raise Exception(f"合并PDF时发生错误: {str(e)}")


def main():
    """测试函数"""
    # 测试用法
    folder_path = r"C:\test\screenshots"  # 替换为实际路径
    splitter = ScreenshotSplitter(folder_path, margin_size_mm=20)
    result = splitter.process_screenshots()
    print(f"处理完成: {result}")


if __name__ == "__main__":
    main() 