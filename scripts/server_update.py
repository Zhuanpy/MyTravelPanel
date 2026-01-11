#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器自动更新脚本

使用方法:
    cd /var/www/MyTravelPanel
    source venv/bin/activate
    python scripts/server_update.py

功能:
    1. 拉取最新代码
    2. 自动执行数据库迁移
    3. 重启 Flask 服务
"""

import os
import sys
import subprocess
from datetime import datetime

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 迁移脚本目录
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')

# 迁移记录文件
MIGRATION_LOG = os.path.join(SCRIPTS_DIR, '.migration_history')


def log(msg, level='INFO'):
    """输出日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")


def run_command(cmd, cwd=None):
    """运行系统命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or PROJECT_ROOT,
            capture_output=True, text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)


def get_executed_migrations():
    """获取已执行的迁移列表"""
    if os.path.exists(MIGRATION_LOG):
        with open(MIGRATION_LOG, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def mark_migration_executed(script_name):
    """标记迁移已执行"""
    with open(MIGRATION_LOG, 'a') as f:
        f.write(f"{script_name}\n")


def get_pending_migrations():
    """获取待执行的迁移脚本"""
    executed = get_executed_migrations()
    pending = []

    # 查找所有日期开头的迁移脚本 (格式: YYYYMMDD_*.py)
    for filename in sorted(os.listdir(SCRIPTS_DIR)):
        if filename.endswith('.py') and filename[:8].isdigit():
            # 排除特殊脚本
            if filename in ['server_update.py']:
                continue
            # 排除已执行的
            if filename in executed:
                continue
            # 排除检查/验证类脚本（只执行迁移类脚本）
            if any(x in filename for x in ['_check_', '_verify_', '_test_']):
                continue
            pending.append(filename)

    return pending


def pull_latest_code():
    """拉取最新代码"""
    log("拉取最新代码...")
    success, stdout, stderr = run_command("git pull")
    if success:
        log("✓ 代码更新成功")
        if stdout.strip():
            print(stdout)
        return True
    else:
        log(f"✗ 代码更新失败: {stderr}", 'ERROR')
        return False


def run_migrations():
    """执行数据库迁移"""
    pending = get_pending_migrations()

    if not pending:
        log("没有待执行的迁移脚本")
        return True

    log(f"发现 {len(pending)} 个待执行的迁移脚本")

    for script in pending:
        script_path = os.path.join(SCRIPTS_DIR, script)
        log(f"执行迁移: {script}")

        try:
            # 动态导入并执行脚本
            import importlib.util
            spec = importlib.util.spec_from_file_location("migration", script_path)
            module = importlib.util.module_from_spec(spec)

            # 执行脚本
            spec.loader.exec_module(module)

            # 如果脚本有 main 函数，调用它
            if hasattr(module, 'main'):
                module.main()
            elif hasattr(module, 'run_migration'):
                module.run_migration()

            # 标记为已执行
            mark_migration_executed(script)
            log(f"✓ {script} 执行成功")

        except Exception as e:
            log(f"✗ {script} 执行失败: {e}", 'ERROR')
            # 迁移失败时询问是否继续
            response = input("是否继续执行其他迁移? (y/n): ").strip().lower()
            if response != 'y':
                return False

    return True


def restart_service():
    """重启 Flask 服务"""
    log("重启服务...")

    # 尝试不同的重启命令
    restart_commands = [
        "sudo systemctl restart mytravel",
        "sudo service mytravel restart",
        "sudo supervisorctl restart mytravel",
    ]

    for cmd in restart_commands:
        success, stdout, stderr = run_command(cmd)
        if success:
            log("✓ 服务重启成功")
            return True

    log("⚠ 无法自动重启服务，请手动重启", 'WARN')
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("MyTravelPanel 服务器更新")
    print("=" * 60)
    print()

    # 1. 拉取最新代码
    if not pull_latest_code():
        log("更新中止", 'ERROR')
        sys.exit(1)

    print()

    # 2. 执行数据库迁移
    log("检查数据库迁移...")
    if not run_migrations():
        log("迁移失败，更新中止", 'ERROR')
        sys.exit(1)

    print()

    # 3. 重启服务
    restart_service()

    print()
    print("=" * 60)
    log("✓ 更新完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
