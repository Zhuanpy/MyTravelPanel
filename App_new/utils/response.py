"""
统一API响应格式模块
"""
from typing import Any, Dict, List, Optional
from flask import jsonify, request
from datetime import datetime


class APIResponse:
    """统一的API响应格式"""
    
    def __init__(self, success: bool = True, data: Any = None, 
                 message: str = "", errors: List[str] = None, 
                 status_code: int = 200, meta: Dict[str, Any] = None):
        self.success = success
        self.data = data
        self.message = message
        self.errors = errors or []
        self.status_code = status_code
        self.meta = meta or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        response = {
            'success': self.success,
            'message': self.message,
            'timestamp': self.timestamp
        }
        
        if self.data is not None:
            response['data'] = self.data
        
        if self.errors:
            response['errors'] = self.errors
        
        if self.meta:
            response['meta'] = self.meta
        
        return response
    
    def to_response(self):
        """转换为Flask响应对象"""
        return jsonify(self.to_dict()), self.status_code
    
    @classmethod
    def success(cls, data: Any = None, message: str = "Success", 
                status_code: int = 200, meta: Dict[str, Any] = None):
        """创建成功响应"""
        return cls(
            success=True,
            data=data,
            message=message,
            status_code=status_code,
            meta=meta
        )
    
    @classmethod
    def error(cls, message: str = "Error", errors: List[str] = None,
              status_code: int = 400, data: Any = None):
        """创建错误响应"""
        return cls(
            success=False,
            data=data,
            message=message,
            errors=errors,
            status_code=status_code
        )
    
    @classmethod
    def validation_error(cls, errors: List[str], message: str = "Validation failed"):
        """创建验证错误响应"""
        return cls(
            success=False,
            message=message,
            errors=errors,
            status_code=422
        )
    
    @classmethod
    def not_found(cls, message: str = "Resource not found"):
        """创建404响应"""
        return cls(
            success=False,
            message=message,
            status_code=404
        )
    
    @classmethod
    def unauthorized(cls, message: str = "Unauthorized"):
        """创建401响应"""
        return cls(
            success=False,
            message=message,
            status_code=401
        )
    
    @classmethod
    def forbidden(cls, message: str = "Forbidden"):
        """创建403响应"""
        return cls(
            success=False,
            message=message,
            status_code=403
        )
    
    @classmethod
    def internal_error(cls, message: str = "Internal server error"):
        """创建500响应"""
        return cls(
            success=False,
            message=message,
            status_code=500
        )


class PaginationMeta:
    """分页元数据"""
    
    def __init__(self, page: int, per_page: int, total: int, pages: int,
                 has_next: bool, has_prev: bool):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = pages
        self.has_next = has_next
        self.has_prev = has_prev
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'pagination': {
                'page': self.page,
                'per_page': self.per_page,
                'total': self.total,
                'pages': self.pages,
                'has_next': self.has_next,
                'has_prev': self.has_prev
            }
        }
    
    @classmethod
    def from_pagination(cls, pagination):
        """从SQLAlchemy分页对象创建"""
        return cls(
            page=pagination.page,
            per_page=pagination.per_page,
            total=pagination.total,
            pages=pagination.pages,
            has_next=pagination.has_next,
            has_prev=pagination.has_prev
        )


def success_response(data: Any = None, message: str = "Success", 
                    status_code: int = 200, meta: Dict[str, Any] = None):
    """快捷成功响应函数"""
    return APIResponse.success(data, message, status_code, meta).to_response()


def error_response(message: str = "Error", errors: List[str] = None,
                  status_code: int = 400, data: Any = None):
    """快捷错误响应函数"""
    return APIResponse.error(message, errors, status_code, data).to_response()


def paginated_response(items: List[Any], pagination, message: str = "Success"):
    """分页响应函数"""
    meta = PaginationMeta.from_pagination(pagination).to_dict()
    return APIResponse.success(
        data=items,
        message=message,
        meta=meta
    ).to_response()


def handle_service_response(service_response, success_status_code: int = 200):
    """处理服务层响应"""
    if service_response.success:
        return APIResponse.success(
            data=service_response.data,
            message=service_response.message,
            status_code=success_status_code
        ).to_response()
    else:
        return APIResponse.error(
            message=service_response.message,
            errors=service_response.errors,
            status_code=400
        ).to_response()


class ResponseBuilder:
    """响应构建器，支持链式调用"""
    
    def __init__(self):
        self._success = True
        self._data = None
        self._message = ""
        self._errors = []
        self._status_code = 200
        self._meta = {}
    
    def success(self, success: bool = True):
        """设置成功状态"""
        self._success = success
        return self
    
    def data(self, data: Any):
        """设置数据"""
        self._data = data
        return self
    
    def message(self, message: str):
        """设置消息"""
        self._message = message
        return self
    
    def errors(self, errors: List[str]):
        """设置错误列表"""
        self._errors = errors
        return self
    
    def status_code(self, status_code: int):
        """设置状态码"""
        self._status_code = status_code
        return self
    
    def meta(self, meta: Dict[str, Any]):
        """设置元数据"""
        self._meta = meta
        return self
    
    def build(self):
        """构建响应"""
        return APIResponse(
            success=self._success,
            data=self._data,
            message=self._message,
            errors=self._errors,
            status_code=self._status_code,
            meta=self._meta
        ).to_response()


# 便捷的响应构建器实例
response = ResponseBuilder()
