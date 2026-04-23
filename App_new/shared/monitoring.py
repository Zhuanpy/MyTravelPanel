# -*- coding: utf-8 -*-
"""
性能监控模块：慢请求 + 慢 SQL 日志

用途：定位 CPU 飙高的根因。

功能：
1. 慢请求日志：每个 HTTP 请求超过阈值时，记录方法/路径/耗时/SQL数/SQL总耗时/用户
2. 慢 SQL 日志：每条 SQL 超过阈值时，单独记录 SQL 语句和参数

日志文件：
- logs/slow_request.log
- logs/slow_query.log

配置项（Config 中可调整）：
- SLOW_REQUEST_THRESHOLD_MS：慢请求阈值，默认 1000ms
- SLOW_QUERY_THRESHOLD_MS：慢 SQL 阈值，默认 500ms
- MONITORING_ENABLED：总开关，默认 True
"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from flask import g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine


# 不需要记录的路径前缀（静态资源、健康检查等噪音请求）
SKIP_PATH_PREFIXES = ('/static/', '/favicon.ico', '/favico.ico')

# 模块级标志，防止 SQLAlchemy 事件被重复注册（同进程多次 create_app）
_sa_events_registered = False


def _make_logger(name: str, log_path: str) -> logging.Logger:
    """创建独立的 RotatingFileHandler 日志器，避免污染主日志"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 单文件 10MB
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    return logger


def _should_skip(path: str) -> bool:
    return any(path.startswith(p) for p in SKIP_PATH_PREFIXES)


def _get_user_info() -> str:
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return f"user={current_user.id}({getattr(current_user, 'username', '?')})"
    except Exception:
        pass
    return "user=anonymous"


def _register_sa_events(query_logger: logging.Logger, slow_query_ms: int):
    """注册 SQLAlchemy 引擎事件（监听所有 Engine 实例）"""

    @event.listens_for(Engine, 'before_cursor_execute')
    def _before(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()

    @event.listens_for(Engine, 'after_cursor_execute')
    def _after(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.perf_counter() - context._query_start_time) * 1000

        # 累加到当前请求的统计
        try:
            if hasattr(g, '_monitor_query_count'):
                g._monitor_query_count += 1
                g._monitor_query_total_ms += elapsed_ms
                if elapsed_ms >= slow_query_ms:
                    g._monitor_slow_queries.append((elapsed_ms, statement))
        except RuntimeError:
            # 不在请求上下文（如后台 APScheduler 任务）
            pass

        # 单独写慢 SQL 日志
        if elapsed_ms >= slow_query_ms:
            stmt_preview = ' '.join(str(statement).split())[:500]
            params_preview = str(parameters)[:200]
            try:
                path = request.path
                user = _get_user_info()
            except RuntimeError:
                path = '-'
                user = 'background'
            query_logger.info(
                f"slow_sql elapsed={elapsed_ms:.1f}ms path={path} {user} | "
                f"sql={stmt_preview} | params={params_preview}"
            )


def _register_request_hooks(app, request_logger: logging.Logger, slow_request_ms: int):
    """注册 Flask 请求生命周期钩子"""

    @app.before_request
    def _monitor_before():
        if _should_skip(request.path):
            return
        g._monitor_start_time = time.perf_counter()
        g._monitor_query_count = 0
        g._monitor_query_total_ms = 0.0
        g._monitor_slow_queries = []

    @app.after_request
    def _monitor_after(response):
        if _should_skip(request.path) or not hasattr(g, '_monitor_start_time'):
            return response

        elapsed_ms = (time.perf_counter() - g._monitor_start_time) * 1000

        if elapsed_ms >= slow_request_ms:
            request_logger.info(
                f"slow_request method={request.method} path={request.path} "
                f"endpoint={request.endpoint} status={response.status_code} "
                f"elapsed={elapsed_ms:.1f}ms "
                f"query_count={g._monitor_query_count} "
                f"query_total={g._monitor_query_total_ms:.1f}ms "
                f"slow_query_count={len(g._monitor_slow_queries)} "
                f"{_get_user_info()}"
            )
            for elapsed, stmt in g._monitor_slow_queries[:3]:
                preview = ' '.join(str(stmt).split())[:200]
                request_logger.info(f"  └─ slow_sql {elapsed:.1f}ms: {preview}")

        return response


def init_monitoring(app):
    """注册性能监控到 Flask app"""
    if not app.config.get('MONITORING_ENABLED', True):
        return

    slow_request_ms = app.config.get('SLOW_REQUEST_THRESHOLD_MS', 1000)
    slow_query_ms = app.config.get('SLOW_QUERY_THRESHOLD_MS', 500)

    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'logs'
    )
    os.makedirs(log_dir, exist_ok=True)

    request_logger = _make_logger('monitoring.slow_request', os.path.join(log_dir, 'slow_request.log'))
    query_logger = _make_logger('monitoring.slow_query', os.path.join(log_dir, 'slow_query.log'))

    # SQLAlchemy 事件全局注册一次
    global _sa_events_registered
    if not _sa_events_registered:
        _register_sa_events(query_logger, slow_query_ms)
        _sa_events_registered = True

    # 请求钩子按 app 注册
    _register_request_hooks(app, request_logger, slow_request_ms)

    app.logger.info(
        f"性能监控已启用 | slow_request>{slow_request_ms}ms | slow_query>{slow_query_ms}ms"
    )
