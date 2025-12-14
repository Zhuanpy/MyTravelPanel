# -*- coding: utf-8 -*-
"""
任务提醒服务
自动从业务数据生成提醒任务
"""

from App_new.exts import db
from App_new.shared.models.Utilsmodels import Todo
from datetime import datetime, timedelta
from flask import current_app


class TaskReminderService:
    """任务提醒服务类"""
    
    def generate_visa_reminders(self, days_ahead=7):
        """
        从签证项目生成提醒任务
        days_ahead: 提前多少天创建提醒
        """
        try:
            # 尝试导入签证项目模型（根据实际路径调整）
            try:
                from App_new.business.visa.models.visa import VisaProject
            except ImportError:
                # 如果找不到模型，记录警告并返回
                current_app.logger.warning('签证项目模型未找到，跳过签证提醒生成')
                return 0
            
            today = datetime.now().date()
            target_date = today + timedelta(days=days_ahead)
            
            # 查询即将到期的签证项目
            # 注意：需要根据实际的VisaProject模型字段调整
            # 假设有expiry_date或due_date字段
            visa_projects = []
            try:
                # 尝试查询，如果字段不存在会抛出异常
                if hasattr(VisaProject, 'expiry_date'):
                    visa_projects = VisaProject.query.filter(
                        VisaProject.expiry_date >= today,
                        VisaProject.expiry_date <= target_date
                    ).all()
                elif hasattr(VisaProject, 'due_date'):
                    visa_projects = VisaProject.query.filter(
                        VisaProject.due_date >= today,
                        VisaProject.due_date <= target_date
                    ).all()
            except Exception as e:
                current_app.logger.warning(f'查询签证项目时出错: {str(e)}')
                return 0
            
            created_count = 0
            for project in visa_projects:
                # 检查是否已存在提醒任务
                existing = Todo.query.filter_by(
                    source_type='visa',
                    source_id=project.id,
                    is_completed=False
                ).first()
                
                if not existing:
                    # 获取到期日期
                    expiry_date = getattr(project, 'expiry_date', None) or getattr(project, 'due_date', None)
                    if not expiry_date:
                        continue
                    
                    # 创建提醒任务
                    try:
                        todo = Todo.create(
                            title=f'[签证提醒] {getattr(project, "applicant_name", "")} - {getattr(project, "visa_type", "")}',
                            description=f'项目ID: {project.id}\n签证类型: {getattr(project, "visa_type", "")}\n申请人: {getattr(project, "applicant_name", "")}\n到期日期: {expiry_date}',
                            category='visa_reminder',
                            priority=1,  # 高优先级
                            due_date=datetime.combine(expiry_date, datetime.min.time()) if isinstance(expiry_date, type(today)) else expiry_date,
                            source_type='visa',
                            source_id=project.id,
                            reminder_days_before=days_ahead,
                            auto_generated=True,
                            user_id=getattr(project, 'staff_id', None)  # 可以设置为项目负责人
                        )
                        created_count += 1
                        current_app.logger.info(f'创建签证提醒任务: {todo.id}')
                    except Exception as e:
                        current_app.logger.error(f'创建签证提醒任务失败: {str(e)}')
            
            return created_count
            
        except Exception as e:
            current_app.logger.error(f'生成签证提醒失败: {str(e)}')
            return 0
    
    def generate_project_reminders(self, days_ahead=7):
        """
        从项目生成提醒任务
        """
        try:
            from App_new.business.projects.models.project import ProjectHeader
            
            today = datetime.now().date()
            target_date = today + timedelta(days=days_ahead)
            
            # 查询即将到期的项目
            projects = ProjectHeader.query.filter(
                ProjectHeader.due_date >= today,
                ProjectHeader.due_date <= target_date,
                ProjectHeader.status != 'completed'
            ).all()
            
            created_count = 0
            for project in projects:
                # 检查是否已存在提醒任务
                existing = Todo.query.filter_by(
                    source_type='project',
                    source_id=project.id,
                    is_completed=False
                ).first()
                
                if not existing and project.due_date:
                    # 创建提醒任务
                    try:
                        todo = Todo.create(
                            title=f'[项目提醒] {project.project_name or f"项目#{project.id}"}',
                            description=f'项目ID: {project.id}\n项目名称: {project.project_name}\n到期日期: {project.due_date}',
                            category='project_reminder',
                            priority=2,  # 中优先级
                            due_date=datetime.combine(project.due_date, datetime.min.time()) if isinstance(project.due_date, type(today)) else project.due_date,
                            source_type='project',
                            source_id=project.id,
                            reminder_days_before=days_ahead,
                            auto_generated=True,
                            user_id=project.staff_id if hasattr(project, 'staff_id') else None,  # 分配给项目负责人
                            assigned_to=project.staff_id if hasattr(project, 'staff_id') else None
                        )
                        created_count += 1
                        current_app.logger.info(f'创建项目提醒任务: {todo.id}')
                    except Exception as e:
                        current_app.logger.error(f'创建项目提醒任务失败: {str(e)}')
            
            return created_count
            
        except Exception as e:
            current_app.logger.error(f'生成项目提醒失败: {str(e)}')
            return 0
    
    def check_and_create_reminders(self, days_ahead=7):
        """
        检查并创建所有类型的提醒任务
        """
        visa_count = self.generate_visa_reminders(days_ahead)
        project_count = self.generate_project_reminders(days_ahead)
        
        current_app.logger.info(f'自动生成提醒任务完成: 签证{visa_count}个, 项目{project_count}个')
        return visa_count + project_count

