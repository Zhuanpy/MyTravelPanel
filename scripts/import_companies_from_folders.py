#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从文件夹名称自动导入公司信息脚本
"""

import os
import re
import sys
import requests
from datetime import datetime
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Flask应用
from app import app
from App.exts import db
from App.models.projects.BookingProject import CustomerCompany

class CompanyImporter:
    def __init__(self):
        self.companies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '资源', '账单', 'Company')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_company_folders(self):
        """获取所有公司文件夹"""
        if not os.path.exists(self.companies_path):
            print(f"错误：路径不存在 {self.companies_path}")
            return []
        
        folders = []
        for item in os.listdir(self.companies_path):
            item_path = os.path.join(self.companies_path, item)
            if os.path.isdir(item_path):
                folders.append(item)
        
        return sorted(folders)
    
    def parse_company_name(self, folder_name):
        """解析文件夹名称，提取公司信息"""
        # 移除常见的后缀
        name = folder_name.strip()
        
        # 处理PTE LTD后缀
        if name.endswith(' PTE. LTD'):
            name = name[:-9]
        elif name.endswith(' PTE LTD'):
            name = name[:-8]
        
        # 处理CO PTE LTD后缀
        if name.endswith(' CO PTE LTD'):
            name = name[:-11]
        
        # 处理PTE. LTD后缀
        if name.endswith(' PTE. LTD'):
            name = name[:-9]
        
        # 生成公司代码
        company_code = self.generate_company_code(name)
        
        return {
            'company_name': folder_name,
            'company_code': company_code,
            'parsed_name': name
        }
    
    def generate_company_code(self, company_name):
        """生成公司代码"""
        # 提取首字母
        words = company_name.split()
        if len(words) >= 2:
            code = ''.join([word[0].upper() for word in words[:3]])
        else:
            code = company_name[:3].upper()
        
        # 添加时间戳后缀
        timestamp = datetime.now().strftime('%m%d')
        return f"{code}{timestamp}"
    
    def search_company_info(self, company_name):
        """从网络搜索公司信息"""
        try:
            # 这里可以集成各种API来获取公司信息
            # 例如：ACRA API, Google搜索等
            
            # 模拟搜索延迟
            time.sleep(1)
            
            # 返回模拟数据
            return {
                'industry': self.guess_industry(company_name),
                'company_size': self.guess_company_size(company_name),
                'contact_person': '',
                'contact_phone': '',
                'contact_email': '',
                'address': '',
                'remarks': f'从文件夹自动导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            }
        except Exception as e:
            print(f"搜索公司信息失败: {e}")
            return {
                'industry': '其他',
                'company_size': '中型公司',
                'contact_person': '',
                'contact_phone': '',
                'contact_email': '',
                'address': '',
                'remarks': f'从文件夹自动导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            }
    
    def guess_industry(self, company_name):
        """根据公司名称猜测行业"""
        name_lower = company_name.lower()
        
        industry_keywords = {
            'construction': '制造业',
            'engineering': '制造业',
            'builder': '制造业',
            'maintenance': '制造业',
            'builders': '制造业',
            'development': '房地产',
            'group': '房地产',
            'international': '其他',
            'pte': '其他',
            'ltd': '其他'
        }
        
        for keyword, industry in industry_keywords.items():
            if keyword in name_lower:
                return industry
        
        return '其他'
    
    def guess_company_size(self, company_name):
        """根据公司名称猜测规模"""
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['international', 'group', 'development']):
            return '大型公司'
        elif any(word in name_lower for word in ['construction', 'engineering']):
            return '中型公司'
        else:
            return '小型公司'
    
    def check_existing_company(self, company_name):
        """检查公司是否已存在"""
        existing = CustomerCompany.query.filter_by(company_name=company_name).first()
        return existing is not None
    
    def import_company(self, company_data, company_info):
        """导入公司到数据库"""
        try:
            company = CustomerCompany(
                company_name=company_data['company_name'],
                company_code=company_data['company_code'],
                contact_person=company_info['contact_person'],
                contact_phone=company_info['contact_phone'],
                contact_email=company_info['contact_email'],
                address=company_info['address'],
                industry=company_info['industry'],
                company_size=company_info['company_size'],
                status='active',
                remarks=company_info['remarks'],
                created_by='auto_import'
            )
            
            db.session.add(company)
            db.session.commit()
            
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    def run_import(self, dry_run=False):
        """运行导入流程"""
        with app.app_context():
            print("=== 公司信息自动导入脚本 ===")
            print(f"扫描路径: {self.companies_path}")
            print(f"模式: {'预览模式' if dry_run else '实际导入'}")
            print()
            
            # 获取公司文件夹
            folders = self.get_company_folders()
            if not folders:
                print("未找到任何公司文件夹")
                return
            
            print(f"找到 {len(folders)} 个公司文件夹:")
            for folder in folders:
                print(f"  - {folder}")
            print()
            
            # 处理每个公司
            success_count = 0
            error_count = 0
            skipped_count = 0
            
            for i, folder_name in enumerate(folders, 1):
                print(f"[{i}/{len(folders)}] 处理: {folder_name}")
                
                # 解析公司名称
                company_data = self.parse_company_name(folder_name)
                
                # 检查是否已存在
                if self.check_existing_company(company_data['company_name']):
                    print(f"  ⚠️  跳过: 公司已存在")
                    skipped_count += 1
                    continue
                
                # 搜索公司信息
                print(f"  🔍 搜索公司信息...")
                company_info = self.search_company_info(company_data['parsed_name'])
                
                # 显示预览信息
                print(f"  📋 公司代码: {company_data['company_code']}")
                print(f"  📋 行业: {company_info['industry']}")
                print(f"  📋 规模: {company_info['company_size']}")
                
                if dry_run:
                    print(f"  ✅ 预览完成")
                    success_count += 1
                else:
                    # 实际导入
                    print(f"  💾 导入数据库...")
                    success, error = self.import_company(company_data, company_info)
                    
                    if success:
                        print(f"  ✅ 导入成功")
                        success_count += 1
                    else:
                        print(f"  ❌ 导入失败: {error}")
                        error_count += 1
                
                print()
            
            # 显示结果
            print("=== 导入结果 ===")
            print(f"总计: {len(folders)} 个公司")
            print(f"成功: {success_count} 个")
            print(f"失败: {error_count} 个")
            print(f"跳过: {skipped_count} 个")
            
            if not dry_run and success_count > 0:
                print(f"\n✅ 成功导入 {success_count} 个公司到数据库")
            elif dry_run:
                print(f"\n📋 预览完成，可以运行实际导入")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从文件夹自动导入公司信息')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际导入数据库')
    parser.add_argument('--path', type=str, help='指定公司文件夹路径')
    
    args = parser.parse_args()
    
    # 创建导入器
    importer = CompanyImporter()
    
    # 如果指定了路径，更新路径
    if args.path:
        importer.companies_path = args.path
    
    # 运行导入
    try:
        importer.run_import(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 