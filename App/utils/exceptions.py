"""
统一异常处理模块
"""
from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


class TravelPanelException(Exception):
    """自定义基础异常类"""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ValidationError(TravelPanelException):
    """数据验证异常"""
    def __init__(self, message, field=None):
        super().__init__(message, status_code=400)
        self.field = field


class AuthenticationError(TravelPanelException):
    """认证异常"""
    def __init__(self, message="Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(TravelPanelException):
    """授权异常"""
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message, status_code=403)


class ResourceNotFoundError(TravelPanelException):
    """资源未找到异常"""
    def __init__(self, message="Resource not found"):
        super().__init__(message, status_code=404)


class BusinessLogicError(TravelPanelException):
    """业务逻辑异常"""
    def __init__(self, message):
        super().__init__(message, status_code=422)


def register_error_handlers(app):
    """注册全局异常处理器"""
    
    @app.errorhandler(TravelPanelException)
    def handle_travel_panel_exception(error):
        """处理自定义异常"""
        logger.error(f"TravelPanel Exception: {error.message}")
        
        # 检查是否是AJAX请求（包括FormData请求）
        is_ajax = (request.is_json or 
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                  request.headers.get('Content-Type', '').startswith('multipart/form-data'))
        
        if is_ajax:
            return jsonify(error.to_dict()), error.status_code
        else:
            return render_template('errors/error.html', 
                                 error=error), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """处理验证异常"""
        logger.warning(f"Validation Error: {error.message}")
        
        response = {
            'message': error.message,
            'status_code': error.status_code,
            'field': error.field
        }
        
        # 检查是否是AJAX请求（包括FormData请求）
        is_ajax = (request.is_json or 
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                  request.headers.get('Content-Type', '').startswith('multipart/form-data'))
        
        if is_ajax:
            return jsonify(response), error.status_code
        else:
            return render_template('errors/validation_error.html', 
                                 error=error), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        logger.warning(f"404 Error: {request.url}")
        
        # 检查是否是AJAX请求（包括FormData请求）
        is_ajax = (request.is_json or 
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                  request.headers.get('Content-Type', '').startswith('multipart/form-data'))
        
        if is_ajax:
            return jsonify({'error': 'Resource not found', 'status_code': 404}), 404
        else:
            return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理500错误"""
        logger.error(f"Internal Server Error: {str(error)}")
        
        # 检查是否是AJAX请求（包括FormData请求）
        is_ajax = (request.is_json or 
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                  request.headers.get('Content-Type', '').startswith('multipart/form-data'))
        
        if is_ajax:
            return jsonify({'error': 'Internal server error', 'status_code': 500}), 500
        else:
            return render_template('errors/500.html'), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """处理HTTP异常"""
        logger.warning(f"HTTP Exception: {error.code} - {error.description}")
        
        # 检查是否是AJAX请求（包括FormData请求）
        is_ajax = (request.is_json or 
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                  request.headers.get('Content-Type', '').startswith('multipart/form-data'))
        
        if is_ajax:
            return jsonify({
                'error': error.description,
                'status_code': error.code
            }), error.code
        else:
            return render_template('errors/http_error.html', 
                                 error=error), error.code
