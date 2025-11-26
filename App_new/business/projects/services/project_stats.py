# -*- coding: utf-8 -*-
"""
项目统计服务类
包含项目相关的各种统计计算
"""

from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader, CustomerCompany
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.eo import ProjectEO
from datetime import datetime, timedelta
from sqlalchemy import func, and_

class ProjectStatsService:
    """项目统计服务类"""
    
    def __init__(self):
        pass
    
    def get_project_stats(self, project_id):
        """获取单个项目的统计信息"""
        try:
            # 获取项目基本信息
            project = ProjectHeader.query.get(project_id)
            if not project:
                return {}
            
            # 获取REF记录统计
            refs = ProjectRef.query.filter_by(header_id=project_id).all()
            
            # 计算总金额
            total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
            total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
            total_profit = total_selling_price - total_cost_price
            
            # 获取收款记录统计
            receipts = ProjectReceipt.query.filter_by(header_id=project_id).all()
            total_received = sum([float(receipt.amount or 0) for receipt in receipts])
            
            # 计算未收款金额
            balance = total_selling_price - total_received
            
            # 获取EO记录统计（通过REF关联）
            ref_ids = [ref.id for ref in refs]
            eos = ProjectEO.query.filter(ProjectEO.ref_id.in_(ref_ids)).all() if ref_ids else []
            total_eo_amount = sum([float(eo.ref.cost_price or 0) for eo in eos if eo.ref])
            
            return {
                'project_id': project_id,
                'total_selling_price': total_selling_price,
                'total_cost_price': total_cost_price,
                'total_profit': total_profit,
                'total_received': total_received,
                'balance': balance,
                'total_eo_amount': total_eo_amount,
                'ref_count': len(refs),
                'receipt_count': len(receipts),
                'eo_count': len(eos),
                'profit_margin': (total_profit / total_selling_price * 100) if total_selling_price > 0 else 0,
                'payment_ratio': (total_received / total_selling_price * 100) if total_selling_price > 0 else 0
            }
        except Exception as e:
            print(f"获取项目统计失败: {e}")
            return {}
    
    def get_total_stats(self):
        """获取总体统计信息"""
        try:
            # 项目总数统计
            total_projects = ProjectHeader.query.count()
            active_projects = ProjectHeader.query.filter_by(status='active').count()
            completed_projects = ProjectHeader.query.filter_by(status='completed').count()
            draft_projects = ProjectHeader.query.filter_by(status='draft').count()
            
            # 财务统计
            all_projects = ProjectHeader.query.all()
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            total_received = 0
            
            for project in all_projects:
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                receipts = ProjectReceipt.query.filter_by(header_id=project.id).all()
                
                # 计算项目金额
                project_selling = sum([float(ref.selling_price or 0) for ref in refs])
                project_cost = sum([float(ref.cost_price or 0) for ref in refs])
                project_received = sum([float(receipt.amount or 0) for receipt in receipts])
                
                total_revenue += project_selling
                total_cost += project_cost
                total_received += project_received
            
            total_profit = total_revenue - total_cost
            total_balance = total_revenue - total_received
            
            # 本月统计
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            projects_this_month = ProjectHeader.query.filter(
                ProjectHeader.created_at >= current_month_start
            ).count()
            
            completed_this_month = ProjectHeader.query.filter(
                and_(
                    ProjectHeader.status == 'completed',
                    ProjectHeader.updated_at >= current_month_start
                )
            ).count()
            
            # 按类型统计
            type_stats = db.session.query(
                ProjectHeader.type,
                func.count(ProjectHeader.id)
            ).group_by(ProjectHeader.type).all()
            
            # 按状态统计
            status_stats = db.session.query(
                ProjectHeader.status,
                func.count(ProjectHeader.id)
            ).group_by(ProjectHeader.status).all()
            
            return {
                'total_projects': total_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'draft_projects': draft_projects,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'total_received': total_received,
                'total_balance': total_balance,
                'projects_this_month': projects_this_month,
                'completed_this_month': completed_this_month,
                'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
                'payment_ratio': (total_received / total_revenue * 100) if total_revenue > 0 else 0,
                'type_stats': dict(type_stats),
                'status_stats': dict(status_stats)
            }
        except Exception as e:
            print(f"获取总体统计失败: {e}")
            return {}
    
    def get_monthly_stats(self, year=None, month=None):
        """获取月度统计信息"""
        try:
            if year is None:
                year = datetime.now().year
            if month is None:
                month = datetime.now().month
            
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            # 本月创建的项目
            projects_created = ProjectHeader.query.filter(
                and_(
                    ProjectHeader.created_at >= month_start,
                    ProjectHeader.created_at <= month_end
                )
            ).count()
            
            # 本月完成的项目
            projects_completed = ProjectHeader.query.filter(
                and_(
                    ProjectHeader.status == 'completed',
                    ProjectHeader.updated_at >= month_start,
                    ProjectHeader.updated_at <= month_end
                )
            ).count()
            
            # 本月财务统计
            month_projects = ProjectHeader.query.filter(
                and_(
                    ProjectHeader.created_at >= month_start,
                    ProjectHeader.created_at <= month_end
                )
            ).all()
            
            month_revenue = 0
            month_cost = 0
            month_profit = 0
            
            for project in month_projects:
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                project_selling = sum([float(ref.selling_price or 0) for ref in refs])
                project_cost = sum([float(ref.cost_price or 0) for ref in refs])
                
                month_revenue += project_selling
                month_cost += project_cost
            
            month_profit = month_revenue - month_cost
            
            return {
                'year': year,
                'month': month,
                'projects_created': projects_created,
                'projects_completed': projects_completed,
                'revenue': month_revenue,
                'cost': month_cost,
                'profit': month_profit,
                'profit_margin': (month_profit / month_revenue * 100) if month_revenue > 0 else 0
            }
        except Exception as e:
            print(f"获取月度统计失败: {e}")
            return {}
    
    def get_company_stats(self, company_id):
        """获取客户公司的项目统计"""
        try:
            # 获取公司的所有项目
            projects = ProjectHeader.query.filter_by(company_id=company_id).all()
            
            if not projects:
                return {}
            
            total_projects = len(projects)
            active_projects = len([p for p in projects if p.status == 'active'])
            completed_projects = len([p for p in projects if p.status == 'completed'])
            
            # 计算财务统计
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            total_received = 0
            
            for project in projects:
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                receipts = ProjectReceipt.query.filter_by(header_id=project.id).all()
                
                project_selling = sum([float(ref.selling_price or 0) for ref in refs])
                project_cost = sum([float(ref.cost_price or 0) for ref in refs])
                project_received = sum([float(receipt.amount or 0) for receipt in receipts])
                
                total_revenue += project_selling
                total_cost += project_cost
                total_received += project_received
            
            total_profit = total_revenue - total_cost
            total_balance = total_revenue - total_received
            
            return {
                'company_id': company_id,
                'total_projects': total_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'total_received': total_received,
                'total_balance': total_balance,
                'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
                'payment_ratio': (total_received / total_revenue * 100) if total_revenue > 0 else 0
            }
        except Exception as e:
            print(f"获取公司统计失败: {e}")
            return {}
    
    def get_staff_stats(self, staff_id):
        """获取员工的项目统计"""
        try:
            # 获取员工负责的所有项目
            projects = ProjectHeader.query.filter_by(staff_id=staff_id).all()
            
            if not projects:
                return {}
            
            total_projects = len(projects)
            active_projects = len([p for p in projects if p.status == 'active'])
            completed_projects = len([p for p in projects if p.status == 'completed'])
            
            # 计算财务统计
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            
            for project in projects:
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                project_selling = sum([float(ref.selling_price or 0) for ref in refs])
                project_cost = sum([float(ref.cost_price or 0) for ref in refs])
                
                total_revenue += project_selling
                total_cost += project_cost
            
            total_profit = total_revenue - total_cost
            
            return {
                'staff_id': staff_id,
                'total_projects': total_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            }
        except Exception as e:
            print(f"获取员工统计失败: {e}")
            return {}
