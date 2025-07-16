#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复乱码Excel文件的脚本
支持检测和修复多种编码格式的Excel文件
"""

import os
import sys
import pandas as pd
import chardet
from pathlib import Path
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('excel_fix.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExcelFixer:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.backup_path = None
        
    def create_backup(self):
        """创建备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.file_path.stem}_backup_{timestamp}{self.file_path.suffix}"
        self.backup_path = self.file_path.parent / backup_name
        
        try:
            import shutil
            shutil.copy2(self.file_path, self.backup_path)
            logger.info(f"已创建备份文件: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return False
    
    def detect_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                logger.info(f"检测到编码: {result}")
                return result['encoding'], result['confidence']
        except Exception as e:
            logger.error(f"编码检测失败: {e}")
            return None, 0
    
    def try_read_excel(self, file_path, encoding=None, engine=None):
        """尝试读取Excel文件"""
        try:
            if encoding:
                # 如果是CSV格式的Excel，尝试用pandas读取
                df = pd.read_csv(file_path, encoding=encoding)
                return df
            else:
                # 尝试不同的Excel引擎
                if engine == 'openpyxl':
                    df = pd.read_excel(file_path, engine='openpyxl')
                elif engine == 'xlrd':
                    df = pd.read_excel(file_path, engine='xlrd')
                elif engine == 'odf':
                    df = pd.read_excel(file_path, engine='odf')
                else:
                    # 默认尝试
                    df = pd.read_excel(file_path)
                return df
        except Exception as e:
            logger.warning(f"读取失败 (encoding={encoding}, engine={engine}): {e}")
            return None
    
    def fix_excel_file(self):
        """修复Excel文件"""
        logger.info(f"开始修复文件: {self.file_path}")
        
        # 检查文件是否存在
        if not self.file_path.exists():
            logger.error(f"文件不存在: {self.file_path}")
            return False
        
        # 创建备份
        if not self.create_backup():
            return False
        
        # 检测编码
        encoding, confidence = self.detect_encoding(self.file_path)
        logger.info(f"文件编码: {encoding}, 置信度: {confidence}")
        
        # 尝试不同的读取方法
        df = None
        methods_tried = []
        
        # 方法1: 直接读取Excel
        logger.info("尝试方法1: 直接读取Excel")
        df = self.try_read_excel(self.file_path)
        if df is not None:
            methods_tried.append("直接读取Excel")
        
        # 方法2: 使用openpyxl引擎
        if df is None:
            logger.info("尝试方法2: 使用openpyxl引擎")
            df = self.try_read_excel(self.file_path, engine='openpyxl')
            if df is not None:
                methods_tried.append("openpyxl引擎")
        
        # 方法3: 使用xlrd引擎
        if df is None:
            logger.info("尝试方法3: 使用xlrd引擎")
            df = self.try_read_excel(self.file_path, engine='xlrd')
            if df is not None:
                methods_tried.append("xlrd引擎")
        
        # 方法4: 尝试不同编码读取
        if df is None and encoding:
            logger.info(f"尝试方法4: 使用检测到的编码 {encoding}")
            df = self.try_read_excel(self.file_path, encoding=encoding)
            if df is not None:
                methods_tried.append(f"编码 {encoding}")
        
        # 方法5: 尝试常见编码
        if df is None:
            common_encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1', 'cp1252']
            for enc in common_encodings:
                logger.info(f"尝试方法5: 使用编码 {enc}")
                df = self.try_read_excel(self.file_path, encoding=enc)
                if df is not None:
                    methods_tried.append(f"编码 {enc}")
                    break
        
        if df is not None:
            logger.info(f"成功读取文件，使用的方法: {', '.join(methods_tried)}")
            logger.info(f"数据形状: {df.shape}")
            logger.info(f"列名: {list(df.columns)}")
            
            # 保存修复后的文件
            output_path = self.file_path.parent / f"{self.file_path.stem}_fixed{self.file_path.suffix}"
            try:
                df.to_excel(output_path, index=False, engine='openpyxl')
                logger.info(f"修复后的文件已保存: {output_path}")
                
                # 显示前几行数据
                logger.info("前5行数据预览:")
                print(df.head())
                
                return True
            except Exception as e:
                logger.error(f"保存修复文件失败: {e}")
                return False
        else:
            logger.error("所有读取方法都失败了")
            return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python fix_corrupted_excel.py <文件路径>")
        print("示例: python fix_corrupted_excel.py 'E:\\Todays file\\aaa\\202208.xls'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)
    
    # 创建修复器并执行修复
    fixer = ExcelFixer(file_path)
    success = fixer.fix_excel_file()
    
    if success:
        print("\n✅ 文件修复完成!")
        print("请检查生成的修复文件。")
    else:
        print("\n❌ 文件修复失败!")
        print("请检查日志文件 excel_fix.log 获取详细信息。")

if __name__ == "__main__":
    main() 