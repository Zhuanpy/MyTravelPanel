# -*- coding: utf-8 -*-
"""API Token 鉴权辅助

为非浏览器客户端（AI agent、脚本等）提供无状态鉴权，避免依赖浏览器 session
导致频繁掉线、反复登录。

集成方式：
- Flask-Login 的 request_loader：当没有有效 session 时，从请求头加载用户。
- 自定义 CSRFProtect：携带有效 token 的请求跳过 CSRF 校验（token 鉴权天然防 CSRF）。
"""

from flask import g


def extract_request_token(request):
    """从请求中提取令牌，支持多种携带方式：
        X-API-Key: <token>
        Authorization: Bearer <token>
        ?api_key=<token>   （便捷用，安全性较低）
    """
    token = request.headers.get('X-API-Key')
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.lower().startswith('bearer '):
            token = auth_header[7:].strip()
    if not token:
        token = request.args.get('api_key')
    return token or None


def wants_json_response(request):
    """判断该请求是否应该收到 JSON 错误，而不是被 302 重定向到登录页/首页。

    AI agent / 脚本被重定向后拿到的是 HTML 页面，极易误判成「token 过期」而
    错误降级（例如改用账号密码登录浏览器），因此这类请求必须收到明确的
    401/403 JSON。
    """
    return bool(
        extract_request_token(request)
        or request.path.startswith('/api/')
        or request.is_json
        or request.accept_mimetypes.best == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )


def authenticate_request_token(request):
    """校验请求中的令牌，返回对应的 AuthUser 或 None。

    结果缓存在 flask.g 上，避免同一请求内重复查询数据库
    （request_loader 与 CSRF 校验可能各调用一次）。
    """
    if 'api_token_user' in g:
        return g.api_token_user

    user = None
    raw_token = extract_request_token(request)
    if raw_token:
        # 延迟导入，避免模块加载期的循环依赖
        from .models.auth import ApiToken
        user = ApiToken.verify(raw_token)

    g.api_token_user = user
    return user
