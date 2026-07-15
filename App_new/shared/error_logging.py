# -*- coding: utf-8 -*-
"""应用级错误日志：把未捕获异常（HTTP 500）持久化到 logs/error.log

背景：本项目 create_app 载入的是基类 Config（DEBUG=True）。DEBUG 为真时，Flask
会把请求中的未捕获异常**直接抛给 WSGI 层（gunicorn）**，而不调用 app.log_exception。
线上又用 `gunicorn --daemon` 且 stderr 指向 /dev/null，于是报错彻底丢失、无从查起。

因此这里不依赖 app.logger，而是挂 Flask 的 `got_request_exception` 信号 —— 它在
「是否 propagate」判断之前触发，无论 DEBUG 真假、无论异常最终是否被重新抛出，只要
请求处理中抛了未捕获异常就会收到。完整 traceback 落到 logs/error.log，与 gunicorn
怎么启动无关。日志消息里带上出错的 URL 和方法，便于直接定位。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import request, got_request_exception


def _get_error_logger():
    """独立的文件日志器（幂等：重复 create_app 不会重复挂 handler）"""
    logger = logging.getLogger('mtp.error')
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    if any(getattr(h, '_mtp_error_handler', False) for h in logger.handlers):
        return logger

    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'logs'
    )
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'error.log')

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 单文件 10MB
        backupCount=10,
        encoding='utf-8'
    )
    handler.setLevel(logging.ERROR)
    handler._mtp_error_handler = True  # 幂等标记
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    return logger


def init_error_logging(app):
    """挂 got_request_exception 信号，把未捕获异常堆栈写入 logs/error.log"""
    logger = _get_error_logger()

    def _log_request_exception(sender, exception, **extra):
        try:
            path, method = request.path, request.method
        except Exception:
            path, method = '-', '-'
        # exc_info 传异常实例，logging 会自动追加完整 traceback
        logger.error('Exception on %s [%s]' % (path, method), exc_info=exception)

    # 用 app 作为 sender，避免跨 app 串信号；weak=False 防止回调被 GC 掉
    got_request_exception.connect(_log_request_exception, app, weak=False)

    app.logger.info('错误日志已启用 | logs/error.log（未捕获异常记录完整堆栈，与 DEBUG/启动方式无关）')
