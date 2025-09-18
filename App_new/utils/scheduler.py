# -*- coding: utf-8 -*-
"""定时任务调度器"""

import schedule
import time
import threading
from datetime import datetime
from App_new.utils.email_reminder import send_daily_reminders
from App_new.utils.reminder_utils import sync_project_reminders


def run_scheduler():
    """运行定时任务调度器"""
    # 每天上午9点发送提醒邮件
    schedule.every().day.at("09:00").do(send_daily_reminders)
    
    # 每天凌晨2点同步项目提醒到待办事项
    schedule.every().day.at("02:00").do(sync_project_reminders)
    
    print(f"定时任务调度器已启动 - {datetime.now()}")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


def start_scheduler_background():
    """在后台线程中启动调度器"""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("定时任务调度器已在后台启动")


def manual_send_reminders():
    """手动发送提醒邮件（用于测试）"""
    try:
        count = send_daily_reminders()
        print(f"手动发送提醒完成，共发送 {count} 封邮件")
        return count
    except Exception as e:
        print(f"手动发送提醒失败: {e}")
        return 0


def manual_sync_reminders():
    """手动同步项目提醒到待办事项（用于测试）"""
    try:
        count = sync_project_reminders()
        print(f"手动同步提醒完成，共同步 {count} 个项目")
        return count
    except Exception as e:
        print(f"手动同步提醒失败: {e}")
        return 0

