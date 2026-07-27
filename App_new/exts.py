# 插件管理

import os

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app

class _ApiTokenCSRFProtect(CSRFProtect):
    """携带有效 API Token 的请求跳过 CSRF 校验。

    Token 通过请求头鉴权，天然不受 CSRF（跨站 cookie）攻击影响；
    且 AI agent / 脚本无法获取页面里的 CSRF token，否则所有 POST 都会被拦。
    """

    def protect(self):
        from flask import request
        try:
            from .auth.token_auth import authenticate_request_token
            if authenticate_request_token(request) is not None:
                return  # 有效 token，放行
        except Exception:
            pass
        return super().protect()


db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
csrf = _ApiTokenCSRFProtect()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()

# 调度器锁文件路径：保证多 gunicorn worker 下只有一个进程启动 scheduler，
# 避免 job_send_reminders 等任务在每个 worker 里都跑一份（之前导致 OOM 的诱因之一）
_SCHEDULER_LOCK_PATH = '/tmp/mytravelpanel_scheduler.lock'
# 模块级保留 fd 引用，防止被 GC 关闭导致锁释放
_scheduler_lock_fd = None


def _try_acquire_scheduler_lock():
    """
    尝试获取调度器排他文件锁。
    成功 -> 返回 True（当前进程负责跑 scheduler）
    失败 -> 返回 False（已有别的进程持锁）
    fcntl 不可用（如 Windows） -> 返回 True，退化为原行为，避免本地开发挂掉
    """
    global _scheduler_lock_fd
    try:
        import fcntl as _fcntl
    except ImportError:
        return True

    fd = None
    try:
        fd = os.open(_SCHEDULER_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
        _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        _scheduler_lock_fd = fd
        return True
    except BlockingIOError:
        # 已有别的 worker 持锁
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"获取 scheduler 锁失败，退化为单进程模式: {e}")
        return True


def _register_scheduler_jobs(app):
    """注册所有定时任务（仅在持锁的 worker 中调用）"""
    try:
        from App_new.shared.routes.tasks import send_due_todo_reminders
        from App_new.shared.services.task_reminder_service import TaskReminderService
        from apscheduler.triggers.cron import CronTrigger

        # 任务1：发送到期提醒邮件（每15分钟）
        def job_send_reminders():
            with app.app_context():
                send_due_todo_reminders()

        scheduler.add_job(
            id='todo_due_email',
            func=job_send_reminders,
            trigger=IntervalTrigger(minutes=15),
            replace_existing=True
        )
        print("Registered job: todo_due_email (every 15 minutes)")

        # 任务2：自动生成提醒任务（每天凌晨2点）
        def job_generate_reminders():
            with app.app_context():
                service = TaskReminderService()
                service.check_and_create_reminders(days_ahead=7)
                print("自动生成提醒任务完成")

        scheduler.add_job(
            id='auto_generate_reminders',
            func=job_generate_reminders,
            trigger=CronTrigger(hour=2, minute=0),
            replace_existing=True
        )
        print("Registered job: auto_generate_reminders (daily at 2:00 AM)")

        # 任务3：自动从重复清单生成待办事项（每天早上8点）
        def job_generate_checklist_todos():
            with app.app_context():
                from App_new.utils.scheduler import auto_generate_checklist_todos
                auto_generate_checklist_todos()

        scheduler.add_job(
            id='auto_generate_checklist_todos',
            func=job_generate_checklist_todos,
            trigger=CronTrigger(hour=8, minute=0),
            replace_existing=True
        )
        print("Registered job: auto_generate_checklist_todos (daily at 8:00 AM)")

    except Exception as je:
        print(f"注册定时任务失败: {je}")


def init_exts(app):
    # 初始化数据库
    db.init_app(app=app)
    migrate.init_app(app=app, db=db)

    # 初始化CSRF保护
    csrf.init_app(app)

    # 初始化缓存
    cache_config = {
        'CACHE_TYPE': 'simple',  # 使用简单的内存缓存，生产环境可以改用 redis
        'CACHE_DEFAULT_TIMEOUT': 3600  # 默认缓存时间1小时
    }
    app.config.from_mapping(cache_config)
    cache.init_app(app)

    # 初始化Flask-Mail
    mail.init_app(app)

    # 初始化 APScheduler：通过文件锁保证多 worker 下仅一个进程启动调度
    try:
        if not _try_acquire_scheduler_lock():
            print(f"APScheduler skipped (lock held by another worker, pid={os.getpid()})")
        else:
            if not scheduler.running:
                scheduler.start()
                print(f"APScheduler started (pid={os.getpid()})")
            _register_scheduler_jobs(app)
    except Exception as e:
        print(f"APScheduler 启动失败: {e}")

    # 初始化Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.staff_login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    # 用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        from flask import session
        from flask_login import logout_user
        from .auth.models import AuthUser

        user = AuthUser.query.get(int(user_id))
        if user:
            # 检查会话版本是否匹配
            stored_session_version = session.get('session_version')
            user_session_version = user.session_version or 1

            # 如果session中没有版本号（旧会话），或版本号不匹配，强制登出
            if stored_session_version is None:
                session.clear()
                return None
            elif stored_session_version != user_session_version:
                # 版本号不匹配（密码已被修改），强制登出
                session.clear()
                return None
        return user

    # 从请求头加载用户（API Token 鉴权）
    # 当没有有效 session 时，Flask-Login 会调用此函数；
    # 让 AI agent / 脚本可凭 X-API-Key 或 Authorization: Bearer 无状态访问，
    # 不再依赖会频繁掉线的浏览器 session。
    @login_manager.request_loader
    def load_user_from_request(request):
        from .auth.token_auth import authenticate_request_token
        return authenticate_request_token(request)

    # 未授权处理器
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, redirect, url_for, flash, jsonify
        from .auth.token_auth import wants_json_response

        # API 客户端（AI agent / 脚本）必须收到 401 JSON，不能被 302 到登录页：
        # 否则拿到的是登录页 HTML，会被误判成「token 过期」而错误降级到浏览器模式。
        if wants_json_response(request):
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': 'token 缺失/无效/已停用，或该账号无权限。'
                           '请调用 GET /api/hermes/whoami 自检，不要改用账号密码登录。',
            }), 401

        flash('请先登录', 'warning')
        return redirect(url_for('auth_profile.staff_login', next=request.url))

    # 导入模型并创建所有表（如果未跳过）
    if not app.config.get('SKIP_DB_INIT', False):
        with app.app_context():
            try:
                db.create_all()
                print("数据库表创建完成")
            except Exception as e:
                print(f"数据库连接失败: {e}")
                print("提示：请检查数据库连接配置或IP白名单设置")
    else:
        print("跳过数据库初始化")

# 在需要使用模型时在各自的模块中导入
