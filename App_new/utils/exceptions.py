"""
统一异常处理模块

register_error_handlers(app) 由 create_app 调用，负责三件事：
  1. 4xx/5xx 一律走同一个自包含错误页（errors/http_error.html），API 请求返回 JSON
  2. 所有非预期错误写进 logs/error.log —— 这些是「已被 Flask 处理」的异常，
     不会触发 got_request_exception，不显式记录就彻底看不到
  3. CSRF token 失效不再甩一个裸 400 页，而是提示「页面已过期」并退回原页面
"""
from flask import jsonify, render_template, request, flash, redirect
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException
from werkzeug.routing import RequestRedirect
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


def _wants_json():
    """判断该请求应该返回 JSON 而不是错误页面"""
    if request.is_json:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
        return True
    # /api/ 前缀的接口一律按 JSON 处理，避免前端 fetch 拿到一坨 HTML
    if '/api/' in request.path:
        return True
    # 浏览器地址栏访问会带 text/html；纯接口调用通常只接受 json
    accept = request.accept_mimetypes
    return accept.accept_json and not accept.accept_html


def _error_response(code, title, message):
    """统一出口：API 给 JSON，页面给自包含错误页"""
    if _wants_json():
        return jsonify({'success': False, 'error': message, 'status_code': code}), code
    return render_template(
        'errors/http_error.html',
        error_code=code,
        error_title=title,
        error_message=message
    ), code


def register_error_handlers(app):
    """注册全局异常处理器"""
    from App_new.shared.error_logging import log_error

    @app.errorhandler(TravelPanelException)
    def handle_travel_panel_exception(error):
        """处理自定义业务异常"""
        log_error(f'业务异常：{error.message}', error)
        return _error_response(error.status_code, '操作失败', error.message)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """处理数据校验异常（校验失败属于预期内，不写错误日志）"""
        logger.warning(f"Validation Error: {error.message}")
        field_hint = f'（字段：{error.field}）' if error.field else ''
        return _error_response(error.status_code, '数据校验未通过', f'{error.message}{field_hint}')

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """CSRF token 失效

        CSRFProtect 在进入视图前就 abort(400)，视图里的 try/except 完全够不着，
        用户只会看到一个裸 400 页，后台也没有任何记录。这里补上提示和日志。
        """
        log_error(f'CSRF 校验失败：{error.description}')
        message = '页面已过期（登录态或表单令牌失效），请刷新页面后重新提交。'
        if _wants_json():
            return jsonify({'success': False, 'error': message, 'status_code': 400}), 400
        flash(message, 'error')
        # 退回来源页，用户刷新即可拿到新 token；没有来源页就回首页
        return redirect(request.referrer or '/')

    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404（爬虫/扫描很多，不写错误日志，避免刷屏）"""
        logger.warning(f"404 Error: {request.url}")
        return _error_response(404, '页面未找到', '抱歉，您访问的页面不存在或已被删除。')

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """处理其余 HTTP 异常"""
        # RequestRedirect（缺斜杠自动跳转等）也是 HTTPException，绝不能当错误页渲染
        if isinstance(error, RequestRedirect) or (error.code and 300 <= error.code < 400):
            return error

        # 401 由登录流程自己处理，不算异常；其余 4xx/5xx 都留痕
        if error.code != 401:
            log_error(f'HTTP {error.code}：{error.description}')

        title = '服务器开小差了' if (error.code or 500) >= 500 else '请求无法处理'
        return _error_response(error.code or 500, title, error.description or '')

    app.logger.info('全局异常处理器已注册 | 4xx/5xx 统一页面 + 写入 logs/error.log')
