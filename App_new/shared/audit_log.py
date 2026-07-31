# -*- coding: utf-8 -*-
"""删除类操作的审计日志：写入 logs/audit.log

背景：REF 被删除时系统不留任何痕迹 —— 没有软删除、没有审计表、成功路径不写日志。
2026-07 排查孤儿发票时发现 9 张发票的 REF 被删过，但查不到时间、更查不到人，
只能靠 nginx 日志和 binlog 考古。

这里不建表（避免 schema 迁移），沿用 error_logging 的做法挂一个独立的
RotatingFileHandler，与 app.logger / gunicorn 的启动方式无关，保证一定落盘。
删除前的行快照一并记下来，事后可据此还原「删掉的到底是什么」。
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import request
from flask_login import current_user


def _get_audit_logger():
    """独立的审计文件日志器（幂等：重复 create_app 不会重复挂 handler）"""
    logger = logging.getLogger('mtp.audit')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if any(getattr(h, '_mtp_audit_handler', False) for h in logger.handlers):
        return logger

    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'logs'
    )
    os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(
        os.path.join(log_dir, 'audit.log'),
        maxBytes=10 * 1024 * 1024,  # 单文件 10MB
        backupCount=20,             # 审计日志留久一点
        encoding='utf-8'
    )
    handler.setLevel(logging.INFO)
    handler._mtp_audit_handler = True  # 幂等标记
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    return logger


def audit(action, snapshot=None, **fields):
    """记一条审计。审计失败绝不能影响业务，所以整体 try 住。

    action:   操作标识，如 'delete_ref'
    snapshot: 被删除/修改对象的字段快照（dict），会序列化成 JSON 一并记下
    fields:   其它想记的键值，如 ref_id=123, header_id=456
    """
    try:
        try:
            user = current_user.username if current_user and current_user.is_authenticated else 'anonymous'
        except Exception:
            user = 'unknown'
        try:
            source = '%s %s from %s' % (request.method, request.path, request.remote_addr)
        except Exception:
            source = '-'

        parts = ['action=%s' % action, 'user=%s' % user, 'source=%s' % source]
        parts += ['%s=%s' % (k, v) for k, v in fields.items()]
        if snapshot is not None:
            parts.append('snapshot=%s' % json.dumps(snapshot, ensure_ascii=False, default=str))
        _get_audit_logger().info(' | '.join(parts))
    except Exception:
        pass  # 审计永远不阻断业务
