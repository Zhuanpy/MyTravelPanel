"""
数据验证工具模块
"""
import re
from typing import Any, Dict, List, Optional
from .exceptions import ValidationError


class BaseValidator:
    """基础验证器"""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> None:
        """验证必填字段"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required", field=field_name)
    
    @staticmethod
    def validate_string_length(value: str, field_name: str, 
                             min_length: int = 0, max_length: int = None) -> None:
        """验证字符串长度"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field=field_name)
        
        if len(value) < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters long",
                field=field_name
            )
        
        if max_length and len(value) > max_length:
            raise ValidationError(
                f"{field_name} must be no more than {max_length} characters long",
                field=field_name
            )
    
    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> None:
        """验证邮箱格式"""
        if not email:
            return
        
        # 允许的特殊值（不区分大小写）
        allowed_special_values = ['n/a', 'none', '无', 'na', 'null', '']
        if email.lower().strip() in allowed_special_values:
            return
        
        # 标准邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(f"Invalid {field_name} format", field=field_name)
    
    @staticmethod
    def validate_phone(phone: str, field_name: str = "phone") -> None:
        """验证电话号码格式"""
        if not phone:
            return
        
        # 简单的电话号码验证（可根据需要调整）
        phone_pattern = r'^[\+]?[1-9][\d]{3,14}$'
        if not re.match(phone_pattern, phone.replace(' ', '').replace('-', '')):
            raise ValidationError(f"Invalid {field_name} format", field=field_name)
    
    @staticmethod
    def validate_numeric_range(value: float, field_name: str,
                             min_value: float = None, max_value: float = None) -> None:
        """验证数值范围"""
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be at least {min_value}",
                field=field_name
            )
        
        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be no more than {max_value}",
                field=field_name
            )


class ProjectValidator(BaseValidator):
    """项目数据验证器"""
    
    @classmethod
    def validate_project_data(cls, data: Dict[str, Any]) -> None:
        """验证项目数据"""
        # 验证必填字段
        cls.validate_required(data.get('desc'), 'desc')
        cls.validate_required(data.get('company_name'), 'company_name')
        cls.validate_required(data.get('staff_name'), 'staff_name')
        
        # 验证字符串长度
        cls.validate_string_length(
            data.get('desc', ''), 'desc', 
            min_length=1, max_length=200
        )
        
        cls.validate_string_length(
            data.get('company_name', ''), 'company_name', 
            min_length=1, max_length=100
        )
        
        cls.validate_string_length(
            data.get('staff_name', ''), 'staff_name', 
            min_length=1, max_length=50
        )


class UserValidator(BaseValidator):
    """用户数据验证器"""
    
    @classmethod
    def validate_user_data(cls, data: Dict[str, Any]) -> None:
        """验证用户数据"""
        # 验证必填字段
        cls.validate_required(data.get('username'), 'username')
        cls.validate_required(data.get('email'), 'email')
        
        # 验证用户名长度
        cls.validate_string_length(
            data.get('username', ''), 'username',
            min_length=3, max_length=80
        )
        
        # 验证邮箱格式
        cls.validate_email(data.get('email', ''))
        
        # 验证电话号码
        if data.get('phone'):
            cls.validate_phone(data['phone'])


class FlightValidator(BaseValidator):
    """航班数据验证器"""
    
    @classmethod
    def validate_flight_data(cls, data: Dict[str, Any]) -> None:
        """验证航班数据"""
        # 验证必填字段
        cls.validate_required(data.get('flight_number'), 'flight_number')
        cls.validate_required(data.get('schedule_city'), 'schedule_city')
        cls.validate_required(data.get('schedule_timing'), 'schedule_timing')
        
        # 验证航班号格式
        flight_number = data.get('flight_number', '').strip().upper()
        if not re.match(r'^[A-Z]{2}\d{1,4}$', flight_number):
            raise ValidationError(
                "Flight number must be in format: XX123 (2 letters + 1-4 digits)",
                field='flight_number'
            )


class SupplierValidator(BaseValidator):
    """供应商数据验证器"""
    
    VALID_SUPPLIER_TYPES = ['visa', 'flight', 'hotel', 'transport', 'local_operator', 'other']
    
    @classmethod
    def validate_supplier_data(cls, data: Dict[str, Any]) -> None:
        """验证供应商数据"""
        # 验证必填字段
        cls.validate_required(data.get('name'), 'name')
        cls.validate_required(data.get('supplier_type'), 'supplier_type')
        
        # 验证供应商类型
        supplier_type = data.get('supplier_type')
        if supplier_type not in cls.VALID_SUPPLIER_TYPES:
            raise ValidationError(
                f"Invalid supplier type. Must be one of: {', '.join(cls.VALID_SUPPLIER_TYPES)}",
                field='supplier_type'
            )
        
        # 验证联系信息
        if data.get('email'):
            cls.validate_email(data['email'])
        
        if data.get('phone'):
            cls.validate_phone(data['phone'])


def validate_data(data: Dict[str, Any], validator_class, method_name: str = 'validate') -> None:
    """通用数据验证函数"""
    try:
        if hasattr(validator_class, method_name):
            getattr(validator_class, method_name)(data)
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Validation error: {str(e)}")
