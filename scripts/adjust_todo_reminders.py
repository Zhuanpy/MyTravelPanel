#!/usr/bin/env python3
"""
待办事项提醒设置调整脚本

此脚本帮助用户调整待办事项提醒的频率设置，以减少频繁提醒的问题。
"""

import os
import sys
from pathlib import Path

def print_current_settings():
    """打印当前的提醒设置"""
    print("当前待办事项提醒设置：")
    print("-" * 50)
    
    # 从环境变量读取设置
    enabled = os.getenv('TODO_NOTIFICATION_ENABLED', 'True')
    check_interval = int(os.getenv('TODO_CHECK_INTERVAL', 6 * 60 * 60))
    email_interval = int(os.getenv('TODO_EMAIL_INTERVAL', 12 * 60 * 60))
    email_threshold = int(os.getenv('TODO_EMAIL_THRESHOLD', 24))
    desktop_notification = os.getenv('TODO_DESKTOP_NOTIFICATION', 'True')
    
    print(f"提醒功能启用: {enabled}")
    print(f"桌面通知检查间隔: {check_interval//3600} 小时 ({check_interval} 秒)")
    print(f"邮件通知检查间隔: {email_interval//3600} 小时 ({email_interval} 秒)")
    print(f"邮件提醒时间阈值: {email_threshold} 小时")
    print(f"桌面通知启用: {desktop_notification}")
    print("-" * 50)

def suggest_optimizations():
    """建议优化设置"""
    print("\n优化建议：")
    print("1. 如果提醒过于频繁，可以增加检查间隔：")
    print("   - 桌面通知：6小时 → 12小时")
    print("   - 邮件通知：12小时 → 24小时")
    print("\n2. 如果不需要某些类型的通知，可以禁用：")
    print("   - 设置 TODO_DESKTOP_NOTIFICATION=False 禁用桌面通知")
    print("   - 设置 TODO_NOTIFICATION_ENABLED=False 完全禁用提醒")
    print("\n3. 环境变量设置示例：")
    print("   TODO_CHECK_INTERVAL=43200      # 12小时")
    print("   TODO_EMAIL_INTERVAL=86400      # 24小时")
    print("   TODO_DESKTOP_NOTIFICATION=False # 禁用桌面通知")

def generate_env_example():
    """生成优化的环境变量示例"""
    print("\n优化的环境变量设置（.env文件）：")
    print("-" * 50)
    print("# 待办事项通知配置 - 优化版本")
    print("TODO_NOTIFICATION_ENABLED=True")
    print("TODO_CHECK_INTERVAL=43200      # 12小时检查一次")
    print("TODO_EMAIL_INTERVAL=86400      # 24小时发送一次邮件")
    print("TODO_EMAIL_THRESHOLD=24        # 24小时内的待办事项")
    print("TODO_DESKTOP_NOTIFICATION=True # 启用桌面通知")
    print("-" * 50)

def main():
    """主函数"""
    print("待办事项提醒设置调整工具")
    print("=" * 50)
    
    # 打印当前设置
    print_current_settings()
    
    # 提供优化建议
    suggest_optimizations()
    
    # 生成优化配置示例
    generate_env_example()
    
    print("\n使用说明：")
    print("1. 将上述环境变量添加到您的 .env 文件中")
    print("2. 重启应用程序以应用新设置")
    print("3. 系统会自动减少检查频率，减少频繁提醒")
    print("4. 如果连续多次没有待办事项，系统会自动延长检查间隔")

if __name__ == "__main__":
    main() 