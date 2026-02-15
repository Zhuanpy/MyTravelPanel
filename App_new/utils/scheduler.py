# -*- coding: utf-8 -*-
"""定时任务调度器"""

import schedule
import time
import threading
from datetime import datetime, timedelta
from App_new.utils.email_reminder import send_daily_reminders
from App_new.utils.reminder_utils import sync_project_reminders


def auto_generate_checklist_todos():
    """自动从重复清单生成待办事项"""
    from flask import current_app
    from App_new.exts import db
    from App_new.shared.models.Utilsmodels import TodoChecklist, TodoChecklistItem, Todo

    try:
        now = datetime.now()
        current_weekday = now.weekday()  # 0=周一, 6=周日
        current_day = now.day
        today_str = now.strftime('%Y-%m-%d')

        # 查找所有启用的重复清单
        checklists = TodoChecklist.query.filter_by(
            is_recurring=True,
            is_active=True
        ).all()

        generated_total = 0

        for checklist in checklists:
            should_generate = False

            # 检查今天是否已经生成过
            if checklist.last_generated_at:
                last_date = checklist.last_generated_at.strftime('%Y-%m-%d')
                if last_date == today_str:
                    continue  # 今天已生成，跳过

            # 根据重复类型判断是否应该生成
            if checklist.recurrence_type == 'daily':
                should_generate = True
            elif checklist.recurrence_type == 'weekly':
                # 检查今天是否在配置的星期几里
                if checklist.recurrence_days:
                    # recurrence_days 格式: "1,2,3,4,5" (周一到周五)
                    # 注意: 数据库存储的是0=周日，但Python weekday()是0=周一
                    configured_days = [int(d) for d in checklist.recurrence_days.split(',') if d]
                    # 转换: 数据库0=周日 -> Python 6, 数据库1=周一 -> Python 0, etc.
                    python_weekday = (current_weekday + 1) % 7  # 转为0=周日格式
                    if python_weekday in configured_days:
                        should_generate = True
            elif checklist.recurrence_type == 'monthly':
                # 检查今天是否在配置的日期里（如 "1,15" 表示每月1号和15号）
                if checklist.recurrence_days:
                    configured_days = [int(d) for d in checklist.recurrence_days.split(',') if d]
                    if current_day in configured_days:
                        should_generate = True
                else:
                    # 未配置日期，默认每月1号
                    if current_day == 1:
                        should_generate = True

            if not should_generate:
                continue

            # 生成待办事项
            base_date = now
            for item in checklist.items.order_by(TodoChecklistItem.order_index).all():
                # 计算截止日期
                item_due_date = None
                if item.due_days_offset:
                    item_due_date = base_date + timedelta(days=item.due_days_offset)
                elif checklist.default_due_days:
                    item_due_date = base_date + timedelta(days=checklist.default_due_days)

                todo = Todo(
                    title=item.title,
                    description=item.description,
                    priority=item.priority,
                    category=checklist.category,
                    due_date=item_due_date,
                    user_id=checklist.user_id,
                    is_completed=False,
                    assigned_to=item.assigned_to,
                    assigned_by=checklist.user_id if item.assigned_to else None,
                    assigned_at=now if item.assigned_to else None,
                    estimated_hours=item.estimated_hours or 0,
                    source_type='checklist',
                    source_id=checklist.id,
                    auto_generated=True
                )
                db.session.add(todo)
                generated_total += 1

            # 更新最后生成时间
            checklist.last_generated_at = now

        db.session.commit()
        print(f"[{now}] 自动生成清单任务完成，共生成 {generated_total} 个待办事项")
        return generated_total

    except Exception as e:
        print(f"自动生成清单任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def run_scheduler():
    """运行定时任务调度器"""
    # 每天上午9点发送提醒邮件
    schedule.every().day.at("09:00").do(send_daily_reminders)

    # 每天凌晨2点同步项目提醒到待办事项
    schedule.every().day.at("02:00").do(sync_project_reminders)

    # 每天早上8点自动生成重复清单任务
    schedule.every().day.at("08:00").do(auto_generate_checklist_todos)

    # 也可以每小时检查一次（针对设置了具体时间的清单）
    schedule.every().hour.do(auto_generate_checklist_todos)

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


def manual_generate_checklist_todos():
    """手动生成清单任务（用于测试）"""
    try:
        count = auto_generate_checklist_todos()
        print(f"手动生成清单任务完成，共生成 {count} 个待办事项")
        return count
    except Exception as e:
        print(f"手动生成清单任务失败: {e}")
        return 0

