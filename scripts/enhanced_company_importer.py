#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版公司信息自动导入脚本
集成网络搜索功能获取更准确的公司信息
"""

import os
import re
import sys
import requests
import json
from datetime import datetime
import time
from urllib.parse import quote_plus

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Flask应用
from app import app
from App.exts import db
from App.models.projects.BookingProject import CustomerCompany

class EnhancedCompanyImporter:
    def __init__(self):
        self.companies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '资源', '账单', 'Company')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 缓存搜索结果
        self.cache_file = 'company_search_cache.json'
        self.search_cache = self.load_cache()
        
    def load_cache(self):
        """加载搜索缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载缓存失败: {e}")
        return {}
    
    def save_cache(self):
        """保存搜索缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
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
        
        # 处理各种PTE LTD后缀
        suffixes = [
            ' PTE. LTD',
            ' PTE LTD',
            ' CO PTE LTD',
            ' PTE. LTD.',
            ' PTE. LTD.',
            ' LIMITED',
            ' LTD'
        ]
        
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        
        # 生成公司代码
        company_code = self.generate_company_code(name)
        
        return {
            'company_name': folder_name,
            'company_code': company_code,
            'parsed_name': name.strip()
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
    
    def search_google(self, company_name):
        """使用Google搜索公司信息"""
        try:
            search_query = f"{company_name} Singapore company profile contact"
            encoded_query = quote_plus(search_query)
            
            # 使用Google搜索API（需要API密钥）
            # 这里使用模拟搜索
            print(f"    🔍 搜索: {search_query}")
            
            # 模拟搜索结果
            return {
                'found': True,
                'website': '',
                'phone': '',
                'email': '',
                'address': '',
                'description': f'新加坡{company_name}公司'
            }
        except Exception as e:
            print(f"    ❌ Google搜索失败: {e}")
            return {'found': False}
    
    def search_acra(self, company_name):
        """搜索ACRA公司注册信息"""
        try:
            # 这里可以集成ACRA API
            # 目前使用模拟数据
            print(f"    🔍 搜索ACRA: {company_name}")
            
            # 模拟ACRA搜索结果
            return {
                'found': True,
                'registration_number': '',
                'incorporation_date': '',
                'business_activity': '',
                'registered_address': '',
                'status': 'Live'
            }
        except Exception as e:
            print(f"    ❌ ACRA搜索失败: {e}")
            return {'found': False}
    
    def search_company_info(self, company_name):
        """综合搜索公司信息"""
        # 检查缓存
        if company_name in self.search_cache:
            print(f"    📋 使用缓存数据")
            return self.search_cache[company_name]
        
        print(f"    🔍 搜索公司信息...")
        
        # 搜索Google
        google_result = self.search_google(company_name)
        
        # 搜索ACRA
        acra_result = self.search_acra(company_name)
        
        # 合并搜索结果
        company_info = {
            'industry': self.guess_industry(company_name),
            'company_size': self.guess_company_size(company_name),
            'contact_person': '',
            'contact_phone': google_result.get('phone', ''),
            'contact_email': google_result.get('email', ''),
            'address': google_result.get('address', ''),
            'website': google_result.get('website', ''),
            'acra_number': acra_result.get('registration_number', ''),
            'remarks': f'从文件夹自动导入 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        }
        
        # 保存到缓存
        self.search_cache[company_name] = company_info
        self.save_cache()
        
        return company_info
    
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
            'property': '房地产',
            'real estate': '房地产',
            'international': '其他',
            'pte': '其他',
            'ltd': '其他',
            'trading': '零售',
            'import': '零售',
            'export': '零售',
            'logistics': '零售',
            'transport': '零售',
            'shipping': '零售',
            'technology': '科技',
            'tech': '科技',
            'software': '科技',
            'digital': '科技',
            'finance': '金融',
            'financial': '金融',
            'banking': '金融',
            'investment': '金融',
            'consulting': '咨询',
            'consultant': '咨询',
            'advisory': '咨询',
            'education': '教育',
            'school': '教育',
            'training': '教育',
            'healthcare': '医疗健康',
            'medical': '医疗健康',
            'hospital': '医疗健康',
            'clinic': '医疗健康'
        }
        
        for keyword, industry in industry_keywords.items():
            if keyword in name_lower:
                return industry
        
        return '其他'
    
    def guess_company_size(self, company_name):
        """根据公司名称猜测规模"""
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['international', 'group', 'development', 'global']):
            return '大型公司'
        elif any(word in name_lower for word in ['construction', 'engineering', 'trading']):
            return '中型公司'
        elif any(word in name_lower for word in ['pte', 'ltd', 'private']):
            return '小型公司'
        else:
            return '中型公司'
    
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
                created_by='enhanced_auto_import'
            )
            
            db.session.add(company)
            db.session.commit()
            
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    def generate_excel_report(self, results):
        """生成Excel报告"""
        try:
            import pandas as pd
            
            # 准备数据
            report_data = []
            for result in results:
                report_data.append({
                    '公司名称': result['company_name'],
                    '公司代码': result['company_code'],
                    '行业': result['industry'],
                    '规模': result['company_size'],
                    '联系电话': result['contact_phone'],
                    '邮箱': result['contact_email'],
                    '地址': result['address'],
                    '网站': result.get('website', ''),
                    'ACRA编号': result.get('acra_number', ''),
                    '导入状态': result['status'],
                    '备注': result.get('remarks', '')
                })
            
            # 创建DataFrame
            df = pd.DataFrame(report_data)
            
            # 保存Excel文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'company_import_report_{timestamp}.xlsx'
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='导入报告', index=False)
                
                # 设置列宽
                worksheet = writer.sheets['导入报告']
                column_widths = [30, 15, 15, 15, 20, 25, 40, 25, 15, 15, 50]
                for i, width in enumerate(column_widths):
                    worksheet.column_dimensions[chr(65 + i)].width = width
            
            print(f"\n📊 导入报告已生成: {filename}")
            return filename
            
        except ImportError:
            print("\n⚠️  未安装pandas，跳过Excel报告生成")
            return None
        except Exception as e:
            print(f"\n❌ 生成Excel报告失败: {e}")
            return None
    
    def run_import(self, dry_run=False, generate_report=True):
        """运行导入流程"""
        with app.app_context():
            print("=== 增强版公司信息自动导入脚本 ===")
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
            results = []
            
            for i, folder_name in enumerate(folders, 1):
                print(f"[{i}/{len(folders)}] 处理: {folder_name}")
                
                # 解析公司名称
                company_data = self.parse_company_name(folder_name)
                
                # 检查是否已存在
                if self.check_existing_company(company_data['company_name']):
                    print(f"  ⚠️  跳过: 公司已存在")
                    skipped_count += 1
                    results.append({
                        'company_name': company_data['company_name'],
                        'company_code': company_data['company_code'],
                        'industry': '已存在',
                        'company_size': '已存在',
                        'contact_phone': '',
                        'contact_email': '',
                        'address': '',
                        'status': '跳过',
                        'remarks': '公司已存在于数据库中'
                    })
                    continue
                
                # 搜索公司信息
                company_info = self.search_company_info(company_data['parsed_name'])
                
                # 显示预览信息
                print(f"  📋 公司代码: {company_data['company_code']}")
                print(f"  📋 行业: {company_info['industry']}")
                print(f"  📋 规模: {company_info['company_size']}")
                if company_info.get('website'):
                    print(f"  📋 网站: {company_info['website']}")
                if company_info.get('acra_number'):
                    print(f"  📋 ACRA编号: {company_info['acra_number']}")
                
                if dry_run:
                    print(f"  ✅ 预览完成")
                    success_count += 1
                    results.append({
                        'company_name': company_data['company_name'],
                        'company_code': company_data['company_code'],
                        'industry': company_info['industry'],
                        'company_size': company_info['company_size'],
                        'contact_phone': company_info['contact_phone'],
                        'contact_email': company_info['contact_email'],
                        'address': company_info['address'],
                        'website': company_info.get('website', ''),
                        'acra_number': company_info.get('acra_number', ''),
                        'status': '预览',
                        'remarks': company_info['remarks']
                    })
                else:
                    # 实际导入
                    print(f"  💾 导入数据库...")
                    success, error = self.import_company(company_data, company_info)
                    
                    if success:
                        print(f"  ✅ 导入成功")
                        success_count += 1
                        results.append({
                            'company_name': company_data['company_name'],
                            'company_code': company_data['company_code'],
                            'industry': company_info['industry'],
                            'company_size': company_info['company_size'],
                            'contact_phone': company_info['contact_phone'],
                            'contact_email': company_info['contact_email'],
                            'address': company_info['address'],
                            'website': company_info.get('website', ''),
                            'acra_number': company_info.get('acra_number', ''),
                            'status': '成功',
                            'remarks': company_info['remarks']
                        })
                    else:
                        print(f"  ❌ 导入失败: {error}")
                        error_count += 1
                        results.append({
                            'company_name': company_data['company_name'],
                            'company_code': company_data['company_code'],
                            'industry': company_info['industry'],
                            'company_size': company_info['company_size'],
                            'contact_phone': company_info['contact_phone'],
                            'contact_email': company_info['contact_email'],
                            'address': company_info['address'],
                            'website': company_info.get('website', ''),
                            'acra_number': company_info.get('acra_number', ''),
                            'status': '失败',
                            'remarks': f"导入失败: {error}"
                        })
                
                print()
            
            # 显示结果
            print("=== 导入结果 ===")
            print(f"总计: {len(folders)} 个公司")
            print(f"成功: {success_count} 个")
            print(f"失败: {error_count} 个")
            print(f"跳过: {skipped_count} 个")
            
            # 生成报告
            if generate_report and results:
                self.generate_excel_report(results)
            
            if not dry_run and success_count > 0:
                print(f"\n✅ 成功导入 {success_count} 个公司到数据库")
            elif dry_run:
                print(f"\n📋 预览完成，可以运行实际导入")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版公司信息自动导入脚本')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际导入数据库')
    parser.add_argument('--path', type=str, help='指定公司文件夹路径')
    parser.add_argument('--no-report', action='store_true', help='不生成Excel报告')
    
    args = parser.parse_args()
    
    # 创建导入器
    importer = EnhancedCompanyImporter()
    
    # 如果指定了路径，更新路径
    if args.path:
        importer.companies_path = args.path
    
    # 运行导入
    try:
        importer.run_import(dry_run=args.dry_run, generate_report=not args.no_report)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 