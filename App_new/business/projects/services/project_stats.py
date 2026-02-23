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
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_

class ProjectStatsService:
    """项目统计服务类"""

    def __init__(self):
        pass

    def get_optimized_total_stats(self):
        """优化后的总体统计（使用SQL聚合）"""
        try:
            # 项目状态统计 - 单次查询
            status_counts = db.session.query(
                ProjectHeader.status,
                func.count(ProjectHeader.id)
            ).group_by(ProjectHeader.status).all()

            status_dict = dict(status_counts)
            total_projects = sum(status_dict.values())

            # 财务统计 - 使用SQL聚合
            revenue_stats = db.session.query(
                func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_revenue'),
                func.coalesce(func.sum(ProjectRef.cost_price), 0).label('total_cost')
            ).first()

            receipt_stats = db.session.query(
                func.coalesce(func.sum(ProjectReceipt.amount), 0).label('total_received')
            ).filter(ProjectReceipt.status == 'confirmed').first()

            total_revenue = float(revenue_stats.total_revenue or 0)
            total_cost = float(revenue_stats.total_cost or 0)
            total_received = float(receipt_stats.total_received or 0)
            total_profit = total_revenue - total_cost

            return {
                'total_projects': total_projects,
                'active_projects': status_dict.get('active', 0) + status_dict.get('draft', 0),
                'completed_projects': status_dict.get('completed', 0),
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'total_received': total_received,
                'total_balance': total_revenue - total_received,
                'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
                'payment_ratio': (total_received / total_revenue * 100) if total_revenue > 0 else 0
            }
        except Exception as e:
            print(f"获取优化统计失败: {e}")
            return self.get_total_stats()  # 回退到原方法

    def get_warning_stats(self):
        """获取预警统计信息"""
        try:
            today = date.today()

            # 1. 超期未完成项目（active状态且创建超过30天）
            thirty_days_ago = datetime.now() - timedelta(days=30)
            overdue_projects = ProjectHeader.query.filter(
                and_(
                    ProjectHeader.status == 'active',
                    ProjectHeader.created_at < thirty_days_ago
                )
            ).count()

            # 2. 逾期应收款（有未收完的款项且项目已完成超过7天）
            seven_days_ago = datetime.now() - timedelta(days=7)

            # 获取已完成但有未收款的项目
            overdue_receivables_query = db.session.query(
                ProjectHeader.id,
                func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_selling'),
                func.coalesce(func.sum(ProjectReceipt.amount), 0).label('total_received')
            ).outerjoin(
                ProjectRef, ProjectRef.header_id == ProjectHeader.id
            ).outerjoin(
                ProjectReceipt, ProjectReceipt.header_id == ProjectHeader.id
            ).filter(
                and_(
                    ProjectHeader.status == 'completed',
                    ProjectHeader.updated_at < seven_days_ago
                )
            ).group_by(ProjectHeader.id).having(
                func.coalesce(func.sum(ProjectRef.selling_price), 0) > func.coalesce(func.sum(ProjectReceipt.amount), 0)
            )

            overdue_receivables = overdue_receivables_query.count()

            # 计算逾期应收款总额
            overdue_amount = 0
            for row in overdue_receivables_query.all():
                overdue_amount += float(row.total_selling or 0) - float(row.total_received or 0)

            # 3. 低利润项目（利润率低于10%）
            low_profit_count = 0
            # 简化查询：获取每个项目的利润率
            projects_with_refs = db.session.query(
                ProjectHeader.id,
                func.coalesce(func.sum(ProjectRef.selling_price), 0).label('selling'),
                func.coalesce(func.sum(ProjectRef.cost_price), 0).label('cost')
            ).outerjoin(
                ProjectRef, ProjectRef.header_id == ProjectHeader.id
            ).filter(
                ProjectHeader.status.in_(['active', 'completed'])
            ).group_by(ProjectHeader.id).having(
                func.coalesce(func.sum(ProjectRef.selling_price), 0) > 0
            )

            for row in projects_with_refs.all():
                selling = float(row.selling or 0)
                cost = float(row.cost or 0)
                if selling > 0:
                    profit_margin = ((selling - cost) / selling) * 100
                    if profit_margin < 10:
                        low_profit_count += 1

            return {
                'overdue_projects': overdue_projects,
                'overdue_receivables': overdue_receivables,
                'overdue_amount': round(overdue_amount, 2),
                'low_profit_projects': low_profit_count,
                'total_warnings': overdue_projects + overdue_receivables
            }
        except Exception as e:
            print(f"获取预警统计失败: {e}")
            return {
                'overdue_projects': 0,
                'overdue_receivables': 0,
                'overdue_amount': 0,
                'low_profit_projects': 0,
                'total_warnings': 0
            }

    def get_tour_stats(self):
        """获取旅游团运营统计"""
        try:
            from App_new.business.tour.models.TourProject import TourProject, TourGroup

            today = date.today()
            current_month_start = today.replace(day=1)

            # 下个月第一天
            if today.month == 12:
                next_month_start = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month_start = today.replace(month=today.month + 1, day=1)

            # 1. 旅游项目总数
            total_tour_projects = TourProject.query.count()

            # 2. 按状态统计
            status_counts = db.session.query(
                TourProject.project_status,
                func.count(TourProject.id)
            ).group_by(TourProject.project_status).all()
            status_dict = dict(status_counts)

            # 3. 本月出发团数
            departing_this_month = TourGroup.query.filter(
                and_(
                    TourGroup.departure_date >= current_month_start,
                    TourGroup.departure_date < next_month_start
                )
            ).count()

            # 4. 待出发团数（出发日期在今天之后）
            pending_departure = TourGroup.query.filter(
                TourGroup.departure_date > today
            ).count()

            # 5. 进行中团数（出发日期 <= 今天 <= 返回日期）
            ongoing_tours = TourGroup.query.filter(
                and_(
                    TourGroup.departure_date <= today,
                    TourGroup.return_date >= today
                )
            ).count()

            # 6. 已完成团数（返回日期 < 今天）
            completed_tours = TourGroup.query.filter(
                TourGroup.return_date < today
            ).count()

            # 7. 总人数统计
            total_pax = db.session.query(
                func.coalesce(func.sum(TourGroup.pax), 0)
            ).scalar() or 0

            # 8. 平均每团人数
            total_groups = TourGroup.query.count()
            avg_pax = round(total_pax / total_groups, 1) if total_groups > 0 else 0

            # 9. 近7天出发
            seven_days_later = today + timedelta(days=7)
            upcoming_7days = TourGroup.query.filter(
                and_(
                    TourGroup.departure_date >= today,
                    TourGroup.departure_date <= seven_days_later
                )
            ).count()

            return {
                'total_tour_projects': total_tour_projects,
                'status_processing': status_dict.get('处理中', 0),
                'status_pending': status_dict.get('待出行', 0),
                'status_completed': status_dict.get('已完成', 0),
                'status_ignored': status_dict.get('忽略单', 0),
                'total_groups': total_groups,
                'departing_this_month': departing_this_month,
                'pending_departure': pending_departure,
                'ongoing_tours': ongoing_tours,
                'completed_tours': completed_tours,
                'total_pax': total_pax,
                'avg_pax': avg_pax,
                'upcoming_7days': upcoming_7days
            }
        except Exception as e:
            print(f"获取旅游团统计失败: {e}")
            return {
                'total_tour_projects': 0,
                'total_groups': 0,
                'departing_this_month': 0,
                'pending_departure': 0,
                'ongoing_tours': 0,
                'completed_tours': 0,
                'total_pax': 0,
                'avg_pax': 0,
                'upcoming_7days': 0
            }

    def get_top_customers(self, limit=5):
        """获取TOP客户统计"""
        try:
            # 按客户统计项目数和收入
            customer_stats = db.session.query(
                CustomerCompany.id,
                CustomerCompany.name,
                func.count(ProjectHeader.id).label('project_count'),
                func.coalesce(func.sum(ProjectRef.selling_price), 0).label('total_revenue')
            ).join(
                ProjectHeader, ProjectHeader.company_id == CustomerCompany.id
            ).outerjoin(
                ProjectRef, ProjectRef.header_id == ProjectHeader.id
            ).group_by(
                CustomerCompany.id, CustomerCompany.name
            ).order_by(
                func.coalesce(func.sum(ProjectRef.selling_price), 0).desc()
            ).limit(limit).all()

            return [{
                'id': row.id,
                'name': row.name,
                'project_count': row.project_count,
                'total_revenue': round(float(row.total_revenue or 0), 2)
            } for row in customer_stats]
        except Exception as e:
            print(f"获取TOP客户统计失败: {e}")
            return []
    
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
