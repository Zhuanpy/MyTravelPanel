# -*- coding: utf-8 -*-
"""
异步邮件发送：通过线程池在后台发送邮件，避免阻塞 web worker。

背景：之前 send_project_email 同步调用 mail.send() 单封邮件耗时 5 秒，
3 个 gunicorn worker 同时被占住会导致整站半瘫，并加重内存压力。

注意：worker 因 --max-requests 回收时，进行中的发送任务会被丢弃。
对于关键业务邮件如需可靠投递，应改用 Celery/RQ 这类持久化队列。
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 邮件 SMTP 是 I/O 密集型，4 个并发足够用，过多容易被 SMTP 服务器限流
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='async-email')


def send_email_async(app, msg, on_done=None):
    """
    提交一个邮件发送任务到后台线程池，立刻返回。

    Args:
        app: Flask app 实例（必须，后台线程没有 request 上下文）
        msg: flask_mail.Message 实例
        on_done: 可选回调 (success: bool, error: Exception | None)，
                 在 app_context 内执行，可用于更新 DB 状态、清理临时文件
    """

    def _run():
        with app.app_context():
            from App_new.exts import mail
            success = False
            error = None
            try:
                mail.send(msg)
                success = True
                logger.info(
                    f"async email sent: subject={msg.subject!r}, recipients={msg.recipients}"
                )
            except Exception as e:
                error = e
                logger.error(
                    f"async email failed: subject={msg.subject!r}, error={e}",
                    exc_info=True,
                )
            if on_done:
                try:
                    on_done(success, error)
                except Exception as cb_e:
                    logger.error(f"邮件回调执行失败: {cb_e}", exc_info=True)

    _executor.submit(_run)


def cleanup_temp_files(paths):
    """删除临时附件文件，安静地忽略错误"""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {p}, {e}")
