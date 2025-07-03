"""
项目管理服务
"""
from typing import Dict, Any
from datetime import datetime, date
from sqlalchemy import or_
from flask import current_app

from .base_service import BaseService, ServiceResponse
from App.models.projects.BookingProject import ProjectHeader, Customer
from ..utils.validators import ProjectValidator
from ..utils.exceptions import ValidationError, BusinessLogicError, ResourceNotFoundError


class ProjectService(BaseService):
    """项目管理服务"""
    
    model = ProjectHeader
    
    @classmethod
    def validate_create_data(cls, data: Dict[str, Any]) -> None:
        """验证创建项目数据"""
        ProjectValidator.validate_project_data(data)
    
    @classmethod
    def validate_update_data(cls, data: Dict[str, Any], instance: ProjectHeader) -> None:
        """验证更新项目数据"""
        # 只验证提供的字段
        if 'desc' in data:
            ProjectValidator.validate_project_data(data)
    
    @classmethod
    def create_project_with_customer(cls, project_data: Dict[str, Any], 
                                   customer_data: Dict[str, Any] = None) -> ServiceResponse:
        """创建项目并关联客户"""
        try:
            # 如果提供了客户数据，先创建或获取客户（暂时注释掉，因为ProjectHeader模型没有customer_id字段）
            # customer = None
            # if customer_data:
            #     customer = CustomerService.create_or_get_customer(customer_data)
            #     project_data['customer_id'] = customer.id
            
            # 生成项目编号
            if 'hid' not in project_data:
                project_data['hid'] = ProjectHeader.generate_hid()
            
            # 创建项目
            project = cls.create(project_data)
            
            return ServiceResponse.success_response(
                data=project.to_dict() if hasattr(project, 'to_dict') else project,
                message="Project created successfully"
            )
            
        except ValidationError as e:
            return ServiceResponse.error_response(message=str(e))
        except BusinessLogicError as e:
            return ServiceResponse.error_response(message=str(e))
        except Exception as e:
            current_app.logger.error(f"Unexpected error creating project: {str(e)}")
            return ServiceResponse.error_response(message="Failed to create project")
    

    
    @classmethod
    def get_project_with_details(cls, project_id: int) -> ServiceResponse:
        """获取项目详细信息，包括关联数据"""
        try:
            project = cls.get_by_id(project_id)
            
            # 获取项目相关的所有数据
            project_data = {
                'project': project.to_dict() if hasattr(project, 'to_dict') else project,
                'refs': [ref.to_dict() if hasattr(ref, 'to_dict') else ref for ref in project.refs],
                'total_refs': len(project.refs),
                'total_amount': sum(ref.selling_price or 0 for ref in project.refs),
                'total_cost': sum(ref.cost_price or 0 for ref in project.refs)
            }
            
            return ServiceResponse.success_response(
                data=project_data,
                message="Project details retrieved successfully"
            )
            
        except ResourceNotFoundError as e:
            return ServiceResponse.error_response(message=str(e))
        except Exception as e:
            current_app.logger.error(f"Error getting project details: {str(e)}")
            return ServiceResponse.error_response(message="Failed to get project details")
    
    @classmethod
    def search_projects(cls, query: str = None, status: str = None, 
                       page: int = 1, per_page: int = 20) -> ServiceResponse:
        """搜索项目"""
        try:
            search_query = cls.model.query
            
            # 文本搜索
            if query:
                search_query = search_query.filter(
                    or_(
                        cls.model.desc.ilike(f'%{query}%'),
                        cls.model.hid.ilike(f'%{query}%'),
                        cls.model.company_name.ilike(f'%{query}%')
                    )
                )
            
            # 状态过滤
            if status:
                search_query = search_query.filter(cls.model.status == status)
            
            # 日期范围过滤（暂时注释掉，因为ProjectHeader模型没有start_date和end_date字段）
            # if start_date:
            #     search_query = search_query.filter(cls.model.start_date >= start_date)
            # if end_date:
            #     search_query = search_query.filter(cls.model.end_date <= end_date)
            
            # 分页
            pagination = search_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            result = {
                'items': [item.to_dict() if hasattr(item, 'to_dict') else item for item in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
            
            return ServiceResponse.success_response(
                data=result,
                message="Projects retrieved successfully"
            )
            
        except Exception as e:
            current_app.logger.error(f"Error searching projects: {str(e)}")
            return ServiceResponse.error_response(message="Failed to search projects")
    
    @classmethod
    def get_project_statistics(cls) -> ServiceResponse:
        """获取项目统计信息"""
        try:
            from sqlalchemy import func
            
            stats = {
                'total_projects': cls.model.query.count(),
                'active_projects': cls.model.query.filter(cls.model.status == 'active').count(),
                'completed_projects': cls.model.query.filter(cls.model.status == 'completed').count(),
                'total_amount': 0,  # ProjectHeader模型没有total_amount字段，暂时设为0
                'projects_by_status': {}
            }
            
            # 按状态统计
            status_stats = cls.model.query.with_entities(
                cls.model.status, func.count(cls.model.id)
            ).group_by(cls.model.status).all()
            
            for status, count in status_stats:
                stats['projects_by_status'][status] = count
            
            return ServiceResponse.success_response(
                data=stats,
                message="Project statistics retrieved successfully"
            )
            
        except Exception as e:
            current_app.logger.error(f"Error getting project statistics: {str(e)}")
            return ServiceResponse.error_response(message="Failed to get project statistics")


class CustomerService(BaseService):
    """客户管理服务"""
    
    model = Customer
    
    @classmethod
    def create_or_get_customer(cls, customer_data: Dict[str, Any]) -> Customer:
        """创建或获取客户"""
        # 根据邮箱或电话查找现有客户
        email = customer_data.get('email')
        phone = customer_data.get('phone')
        
        existing_customer = None
        if email:
            existing_customer = cls.model.query.filter_by(email=email).first()
        elif phone:
            existing_customer = cls.model.query.filter_by(phone=phone).first()
        
        if existing_customer:
            # 更新现有客户信息
            for key, value in customer_data.items():
                if hasattr(existing_customer, key) and value:
                    setattr(existing_customer, key, value)
            return existing_customer
        else:
            # 创建新客户
            return cls.create(customer_data)
