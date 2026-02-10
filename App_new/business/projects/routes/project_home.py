# -*- coding: utf-8 -*-
"""
项目管理首页路由
集中展示项目相关功能入口和统计信息
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from App_new.exts import db
from App_new.business.projects.models.project import ProjectHeader
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.receipt import ProjectReceipt
from App_new.business.projects.models.invoice import ProjectInvoice
from App_new.business.projects.models.eo import ProjectEO
from ..services.project_stats import ProjectStatsService
from App_new.utils.decorators import staff_only
from datetime import datetime, timedelta

# 创建蓝图
project_home = Blueprint('home', __name__)


@project_home.route('/')
@login_required
@staff_only
def index():
    """项目管理首页"""
    try:
        stats_service = ProjectStatsService()

        # 获取总体统计
        total_stats = stats_service.get_optimized_total_stats()

        # 获取预警统计
        warning_stats = stats_service.get_warning_stats()

        # 获取最近项目（最近10个）
        recent_projects_query = ProjectHeader.query.options(
            db.joinedload(ProjectHeader.company)
        ).order_by(ProjectHeader.created_at.desc())

        # 根据员工等级过滤
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1

            if staff_level == 1:
                # 1级员工只能看到自己的项目
                recent_projects_query = recent_projects_query.filter(
                    ProjectHeader.staff_id == current_user.id
                )

        recent_projects = recent_projects_query.limit(10).all()

        # 获取待处理提醒（有提醒且提醒日期在未来7天内）
        today = datetime.now().date()
        seven_days_later = today + timedelta(days=7)

        reminders_query = ProjectHeader.query.filter(
            ProjectHeader.reminder_date.isnot(None),
            ProjectHeader.reminder_date >= today,
            ProjectHeader.reminder_date <= seven_days_later
        ).order_by(ProjectHeader.reminder_date.asc())

        # 同样根据员工等级过滤
        if current_user.role and current_user.role.name == 'staff':
            staff_level = 1
            if current_user.profile:
                staff_level = current_user.profile.staff_level or 1

            if staff_level == 1:
                # 1级员工只能看到自己的项目提醒
                reminders_query = reminders_query.filter(
                    ProjectHeader.staff_id == current_user.id
                )

        upcoming_reminders = reminders_query.limit(5).all()

        # 功能模块列表
        modules = [
            {
                'name': '创建项目',
                'desc': '新建一个项目',
                'icon': 'fas fa-plus-circle',
                'color': 'success',
                'url': 'business_projects.project_create.create_header'
            },
            {
                'name': '项目列表',
                'desc': '查看和管理所有项目',
                'icon': 'fas fa-list',
                'color': 'primary',
                'url': 'business_projects.list.list_projects'
            },
            {
                'name': '收款管理',
                'desc': '管理项目收款记录',
                'icon': 'fas fa-money-bill-wave',
                'color': 'info',
                'url': 'business_projects.project_receipt.receipt_list'
            },
            {
                'name': '发票管理',
                'desc': '管理项目发票',
                'icon': 'fas fa-file-invoice',
                'color': 'warning',
                'url': 'business_projects.project_invoice.invoice_list'
            },
            {
                'name': 'EO管理',
                'desc': '管理Exchange Order',
                'icon': 'fas fa-exchange-alt',
                'color': 'secondary',
                'url': 'business_projects.project_eo.eo_list'
            },
            {
                'name': '邮件模板',
                'desc': '管理邮件模板',
                'icon': 'fas fa-envelope',
                'color': 'dark',
                'url': 'business_projects.detail.email_templates_list'
            }
        ]

        return render_template(
            'business/projects/project_home.html',
            total_stats=total_stats,
            warning_stats=warning_stats,
            recent_projects=recent_projects,
            upcoming_reminders=upcoming_reminders,
            modules=modules
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        # 返回基础页面，即使统计出错
        return render_template(
            'business/projects/project_home.html',
            total_stats={},
            warning_stats={},
            recent_projects=[],
            upcoming_reminders=[],
            modules=[],
            error=str(e)
        )
