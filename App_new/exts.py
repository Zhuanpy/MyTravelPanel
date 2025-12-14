# 插件管理

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()


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

    # 初始化 APScheduler（仅在非调试多进程重复启动时注意幂等）
    try:
        # 避免重复启动：仅在未运行时启动
        if not scheduler.running:
            scheduler.start()
            print("APScheduler started")

        # 在应用上下文内注册任务，显式使用 app 传入，避免 current_app 未绑定
        def _register_jobs(app):
            try:
                from App_new.shared.routes.tasks import send_due_todo_reminders
                from App_new.shared.services.task_reminder_service import TaskReminderService
                from apscheduler.triggers.cron import CronTrigger
                
                # 任务1：发送到期提醒邮件（每15分钟）
                def job_send_reminders():
                    # 手动创建应用上下文
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
                    trigger=CronTrigger(hour=2, minute=0),  # 每天凌晨2点
                    replace_existing=True
                )
                print("Registered job: auto_generate_reminders (daily at 2:00 AM)")
                
            except Exception as je:
                print(f"注册定时任务失败: {je}")

        _register_jobs(app)
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
        from .auth.models import AuthUser
        return AuthUser.query.get(int(user_id))
    
    # 未授权处理器
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, redirect, url_for, flash
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

