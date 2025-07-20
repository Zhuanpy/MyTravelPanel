#!/usr/bin/env python3
"""
测试分页功能脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectHeader

def test_pagination():
    """测试分页功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始测试分页功能...")
            
            # 获取总项目数
            total_projects = ProjectHeader.query.count()
            print(f"总项目数: {total_projects}")
            
            # 测试分页参数
            page = 3
            per_page = 30
            
            # 计算总页数
            total_pages = max(1, (total_projects + per_page - 1) // per_page)
            print(f"总页数: {total_pages}")
            print(f"当前页: {page}")
            
            # 确保页码在有效范围内
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            # 计算当前页的数据范围
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            
            # 获取当前页的数据
            projects = ProjectHeader.query.order_by(ProjectHeader.created_at.desc()).offset(start_index).limit(per_page).all()
            
            print(f"当前页项目数: {len(projects)}")
            print(f"数据范围: {start_index + 1} - {min(end_index, total_projects)}")
            
            # 测试分页对象
            class Pagination:
                def __init__(self, page, per_page, total_count):
                    self.page = page
                    self.per_page = per_page
                    self.total_count = total_count
                    self.pages = total_pages
                    self.has_prev = page > 1
                    self.has_next = page < total_pages
                    self.prev_num = page - 1 if page > 1 else None
                    self.next_num = page + 1 if page < total_pages else None
                    
                def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
                    """生成分页页码列表，支持省略号"""
                    last = 0
                    for num in range(1, self.pages + 1):
                        if num <= left_edge or \
                           (num > self.page - left_current - 1 and num < self.page + right_current) or \
                           num > self.pages - right_edge:
                            if last + 1 != num:
                                yield None  # 省略号
                            yield num
                            last = num
            
            pagination = Pagination(page, per_page, total_projects)
            
            print(f"分页信息:")
            print(f"  当前页: {pagination.page}")
            print(f"  每页数量: {pagination.per_page}")
            print(f"  总数量: {pagination.total_count}")
            print(f"  总页数: {pagination.pages}")
            print(f"  有上一页: {pagination.has_prev}")
            print(f"  有下一页: {pagination.has_next}")
            print(f"  上一页: {pagination.prev_num}")
            print(f"  下一页: {pagination.next_num}")
            
            # 测试页码生成
            print(f"页码列表: {list(pagination.iter_pages())}")
            
            # 测试URL生成
            base_url = "/projects/"
            if pagination.has_prev:
                prev_url = f"{base_url}?page={pagination.prev_num}"
                print(f"上一页URL: {prev_url}")
            
            if pagination.has_next:
                next_url = f"{base_url}?page={pagination.next_num}"
                print(f"下一页URL: {next_url}")
            
            print("分页功能测试完成！")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_pagination() 