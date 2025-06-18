"""
基础服务类
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app
from ..exts import db
from ..utils.exceptions import ValidationError, BusinessLogicError, ResourceNotFoundError


class BaseService:
    """基础服务类，提供通用的CRUD操作"""
    
    model = None  # 子类需要设置对应的模型类
    
    @classmethod
    def create(cls, data: Dict[str, Any], validate: bool = True) -> Any:
        """创建新记录"""
        try:
            if validate and hasattr(cls, 'validate_create_data'):
                cls.validate_create_data(data)
            
            instance = cls.model(**data)
            db.session.add(instance)
            db.session.commit()
            
            current_app.logger.info(f"Created {cls.model.__name__} with ID: {instance.id}")
            return instance
            
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Integrity error creating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Data integrity constraint violation")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error creating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Database operation failed")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError(f"Failed to create {cls.model.__name__.lower()}")
    
    @classmethod
    def get_by_id(cls, id: int) -> Any:
        """根据ID获取记录"""
        instance = cls.model.query.get(id)
        if not instance:
            raise ResourceNotFoundError(f"{cls.model.__name__} with ID {id} not found")
        return instance
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """获取所有记录（分页）"""
        try:
            query = cls.model.query
            
            # 应用过滤器
            for key, value in filters.items():
                if hasattr(cls.model, key) and value is not None:
                    query = query.filter(getattr(cls.model, key) == value)
            
            pagination = query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            return {
                'items': pagination.items,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error fetching {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Failed to fetch data")
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any], validate: bool = True) -> Any:
        """更新记录"""
        try:
            instance = cls.get_by_id(id)
            
            if validate and hasattr(cls, 'validate_update_data'):
                cls.validate_update_data(data, instance)
            
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            db.session.commit()
            
            current_app.logger.info(f"Updated {cls.model.__name__} with ID: {id}")
            return instance
            
        except ResourceNotFoundError:
            raise
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Integrity error updating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Data integrity constraint violation")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error updating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Database operation failed")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error updating {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError(f"Failed to update {cls.model.__name__.lower()}")
    
    @classmethod
    def delete(cls, id: int) -> bool:
        """删除记录"""
        try:
            instance = cls.get_by_id(id)
            
            # 检查是否可以删除（子类可以重写此方法）
            if hasattr(cls, 'can_delete'):
                if not cls.can_delete(instance):
                    raise BusinessLogicError(f"Cannot delete {cls.model.__name__.lower()}")
            
            db.session.delete(instance)
            db.session.commit()
            
            current_app.logger.info(f"Deleted {cls.model.__name__} with ID: {id}")
            return True
            
        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error deleting {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Database operation failed")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error deleting {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError(f"Failed to delete {cls.model.__name__.lower()}")
    
    @classmethod
    def search(cls, query: str, fields: List[str], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """搜索记录"""
        try:
            search_query = cls.model.query
            
            if query and fields:
                conditions = []
                for field in fields:
                    if hasattr(cls.model, field):
                        conditions.append(getattr(cls.model, field).ilike(f'%{query}%'))
                
                if conditions:
                    search_query = search_query.filter(db.or_(*conditions))
            
            pagination = search_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            return {
                'items': pagination.items,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'query': query
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error searching {cls.model.__name__}: {str(e)}")
            raise BusinessLogicError("Search operation failed")


class ServiceResponse:
    """服务响应类，统一返回格式"""
    
    def __init__(self, success: bool = True, data: Any = None, 
                 message: str = "", errors: List[str] = None):
        self.success = success
        self.data = data
        self.message = message
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'errors': self.errors
        }
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "Operation successful"):
        """创建成功响应"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, message: str = "Operation failed", errors: List[str] = None):
        """创建错误响应"""
        return cls(success=False, message=message, errors=errors)
