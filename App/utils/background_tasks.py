"""
待办事项提醒系统

配置说明：
- CHECK_INTERVAL: 桌面通知检查间隔（默认6小时）
- EMAIL_INTERVAL: 邮件通知检查间隔（默认12小时）
- EMAIL_THRESHOLD: 邮件提醒的时间阈值（默认24小时）

环境变量设置示例：
TODO_CHECK_INTERVAL=21600      # 6小时 = 6 * 60 * 60秒
TODO_EMAIL_INTERVAL=43200      # 12小时 = 12 * 60 * 60秒
TODO_EMAIL_THRESHOLD=24        # 24小时内的待办事项

优化特性：
1. 智能检查：连续3次无待办事项后，自动延长检查间隔到24小时
2. 静默模式：减少不必要的日志输出
3. 防重复：确保通知不会过于频繁
"""

from datetime import datetime, timedelta
import threading
from plyer import notification
from App.models.Utilsmodels import Todo
import time
from .send_email import send_email  # 导入邮件发送函数


class TodoReminder:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        self.email_thread = None
        
        # 从配置中获取设置
        self.config = app.config['TODO_NOTIFICATION']
        self.enabled = self.config['ENABLED']
        
        # 优化检查间隔：从2小时改为6小时
        self.check_interval = self.config.get('CHECK_INTERVAL', 6 * 60 * 60)  # 默认6小时检查一次
        self.notification_interval = self.config.get('CHECK_INTERVAL', 6 * 60 * 60)  # 每6小时通知一次
        
        # 邮件检查间隔：从2小时改为12小时
        self.email_interval = self.config.get('EMAIL_INTERVAL', 12 * 60 * 60)  # 默认12小时发送一次邮件
        self.email_threshold = self.config.get('EMAIL_THRESHOLD', 24)  # 24小时内的待办事项
        self.desktop_notification = self.config['DESKTOP_NOTIFICATION']
        
        # 记录上次通知的时间
        self.last_notification_times = {}
        self.last_email_time = None
        
        # 添加静默模式：如果连续多次没有待办事项，减少检查频率
        self.consecutive_empty_checks = 0
        self.max_consecutive_empty_checks = 3  # 连续3次没有待办事项后，延长检查间隔

    def get_upcoming_todos(self, hours_threshold=None):
        try:
            with self.app.app_context():
                now = datetime.now()
            
                # 基础查询：未完成的待办事项
                query = Todo.query.filter(
                Todo.is_completed == False,
                    Todo.due_date > now
                )
                
                # 如果指定了时间阈值，添加额外的过滤条件
                if hours_threshold is not None:
                    future_time = now + timedelta(hours=hours_threshold)
                    query = query.filter(Todo.due_date <= future_time)
                
                todos = query.all()
            return [(todo.id, todo.title, todo.due_date) for todo in todos]
        except Exception as e:
            print(f"查询待办事项时出错: {str(e)}")
            return []

    def show_notification(self, todo_id, title, due_date):
        if not self.desktop_notification:
            return
            
        # 检查是否需要显示通知（避免重复）
        now = datetime.now()
        last_time = self.last_notification_times.get(todo_id)
        
        # 确保6小时内不重复通知
        if last_time and (now - last_time).total_seconds() < self.notification_interval:
            return
            
        time_remaining = due_date - now
        days = time_remaining.days
        hours = time_remaining.seconds // 3600
        minutes = (time_remaining.seconds % 3600) // 60
        
        if days > 0:
            time_str = f"{days}天{hours}小时"
        elif hours > 0:
            time_str = f"{hours}小时{minutes}分钟"
        else:
            time_str = f"{minutes}分钟"

        notification.notify(
            title="待办事项提醒",
            message=f'待办事项"{title}"将在{time_str}后到期',
            app_icon=None,
            timeout=10
        )
        
        # 更新最后通知时间
        self.last_notification_times[todo_id] = now

    def send_email_notification(self, todos):
        if not todos:
            # 减少日志输出频率
            if self.consecutive_empty_checks < 3:
                print("没有需要提醒的待办事项")
            elif self.consecutive_empty_checks % 5 == 0:  # 每5次输出一次日志
                print(f"连续{self.consecutive_empty_checks}次检查没有待办事项")
            self.consecutive_empty_checks += 1
            return
            
        # 重置连续空检查计数
        self.consecutive_empty_checks = 0
            
        # 检查是否需要发送邮件（避免重复）
        now = datetime.now()
        if self.last_email_time:
            time_diff = (now - self.last_email_time).total_seconds()
            if time_diff < self.email_interval:
                print(f"距离上次发送邮件时间太短 ({time_diff} 秒 < {self.email_interval} 秒)，跳过本次发送")
                return
            
        # 构建邮件内容
        email_content = f"以下是{self.email_threshold}小时内即将到期的待办事项：\n\n"
        for todo_id, title, due_date in todos:
            time_remaining = due_date - now  # 使用同一个时间点计算
            hours = time_remaining.seconds // 3600 + time_remaining.days * 24
            minutes = (time_remaining.seconds % 3600) // 60
            
            email_content += f"• {title}\n"
            email_content += f"  剩余时间: {hours}小时{minutes}分钟\n"
            email_content += f"  到期时间: {due_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        try:
            # 再次检查时间间隔（防止执行过程中的时间差）
            if self.last_email_time and (datetime.now() - self.last_email_time).total_seconds() < self.email_interval:
                print("执行过程中检测到时间间隔不足，取消发送")
                return
                
            with self.app.app_context():
                # 更新最后发送时间（在发送之前更新）
                self.last_email_time = now
                
                print(f"正在发送邮件提醒，当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                send_email(
                    subject="待办事项提醒",
                    body=email_content
                )
                print("邮件发送成功")
        except Exception as e:
            print(f"发送邮件通知时出错: {str(e)}")
            # 如果发送失败，重置最后发送时间
            self.last_email_time = None

    def check_todos_email(self):
        while self.running:
            try:
                # 减少日志输出频率
                if self.consecutive_empty_checks < 3:
                    print(f"开始检查需要发送邮件的待办事项，当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                with self.app.app_context():
                    # 获取指定时间内的待办事项
                    todos = self.get_upcoming_todos(hours_threshold=self.email_threshold)
                    if todos:
                        print(f"找到 {len(todos)} 个需要提醒的待办事项")
                    self.send_email_notification(todos)
            except Exception as e:
                print(f"检查待办事项(邮件)时出错: {str(e)}")
            
            # 根据连续空检查次数调整等待时间
            if self.consecutive_empty_checks >= self.max_consecutive_empty_checks:
                # 如果连续多次没有待办事项，延长检查间隔
                adjusted_interval = self.email_interval * 2  # 延长到24小时
                print(f"连续{self.consecutive_empty_checks}次检查无待办事项，延长检查间隔到{adjusted_interval//3600}小时")
                time.sleep(adjusted_interval)
            else:
                # 使用配置的时间间隔
                if self.consecutive_empty_checks < 3:
                    print(f"等待 {self.email_interval//3600} 小时后进行下一次检查")
                time.sleep(self.email_interval)

    def check_todos(self):
        while self.running:
            try:
                with self.app.app_context():
                    todos = self.get_upcoming_todos()
                    for todo_id, title, due_date in todos:
                        self.show_notification(todo_id, title, due_date)
            except Exception as e:
                print(f"检查待办事项时出错: {str(e)}")
            
            # 使用配置的时间间隔
            time.sleep(self.check_interval)

    def start(self):
        if not self.running and self.enabled:
            self.running = True
            
        # 启动桌面通知线程
        if self.desktop_notification:
            self.thread = threading.Thread(target=self.check_todos)
            self.thread.daemon = True
            self.thread.start()
            
            # 启动邮件通知线程
            self.email_thread = threading.Thread(target=self.check_todos_email)
            self.email_thread.daemon = True
            self.email_thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join() 
        if self.email_thread:
            self.email_thread.join() 