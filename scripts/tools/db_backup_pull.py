#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
把服务器上的数据库备份取回本机

db_backup.py 是就地备份，备份和数据库在同一台机器上——能防误删数据、
改错迁移，但防不了整台机器丢失（磁盘坏、服务器被删）。这个脚本补上那一环：
定期把服务器的备份拉回本机，形成异地副本。

存到 backups/db_server/，和本机自己的备份（backups/db/）分开放。
混在一起的话，出事时分不清哪份是服务器的、哪份是本地的，很容易恢复错。

前提：本机到服务器的 SSH 免密登录已配好（密码登录没法自动化）。
配置方法见 docs/数据库备份.md。

用法:
    python scripts/tools/db_backup_pull.py --host 47.84.177.3

    --host        服务器地址（必填，或用环境变量 BACKUP_SSH_HOST）
    --user        SSH 用户，默认 root
    --port        SSH 端口，默认 22
    --remote-dir  服务器上的备份目录，默认 /var/www/MyTravelPanel/backups/db
    --dir         本机存放目录，默认 <项目根>/backups/db_server
    --keep        本机保留最近几份，默认 8
    --identity    SSH 私钥路径，默认用 ssh 的默认查找

只下载本机还没有的文件；下载后校验完整性，坏的直接删掉并计为失败。
退出码 0 成功，非 0 失败。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_backup import PROJECT_ROOT, log, verify_dump, rotate   # noqa: E402

BACKUP_NAME_RE = re.compile(r'^[A-Za-z0-9_]+_\d{8}_\d{6}\.sql\.gz$')

# ssh/scp 在 Windows 上一般来自系统自带的 OpenSSH
WINDOWS_SSH_DIR = r'C:\Windows\System32\OpenSSH'


def find_tool(name):
    found = shutil.which(name)
    if found:
        return found
    if os.name == 'nt':
        candidate = Path(WINDOWS_SSH_DIR) / f'{name}.exe'
        if candidate.exists():
            return str(candidate)
    return None


def ssh_base(args, tool):
    """公共的 ssh/scp 参数"""
    command = [tool]
    if args.identity:
        command += ['-i', args.identity]
    # BatchMode：不交互。没配免密时立刻失败并报错，
    # 而不是挂在密码提示上把定时任务卡死
    command += ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']
    command += ['-P' if tool.endswith(('scp', 'scp.exe')) else '-p', str(args.port)]
    return command


def list_remote(args, ssh):
    """列出服务器备份目录里的文件名"""
    command = ssh_base(args, ssh) + [
        f'{args.user}@{args.host}',
        f'ls -1 {args.remote_dir} 2>/dev/null || true',
    ]
    result = subprocess.run(command, capture_output=True, timeout=60)
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', 'replace').strip()
        log(f'连接服务器失败：{stderr or "退出码 " + str(result.returncode)}')
        if 'Permission denied' in stderr or 'Host key' in stderr:
            log('提示：需要先配好 SSH 免密登录，见 docs/数据库备份.md')
        return None
    names = [n.strip() for n in result.stdout.decode('utf-8', 'replace').splitlines()]
    return [n for n in names if BACKUP_NAME_RE.match(n)]


def fetch(args, scp, name, target_dir):
    """下载单个备份文件，校验通过返回 True"""
    part = target_dir / (name + '.part')
    final = target_dir / name
    command = ssh_base(args, scp) + [
        f'{args.user}@{args.host}:{args.remote_dir}/{name}',
        str(part),
    ]
    result = subprocess.run(command, capture_output=True, timeout=3600)
    if result.returncode != 0:
        log(f'下载失败 {name}：{result.stderr.decode("utf-8", "replace").strip()}')
        part.unlink(missing_ok=True)
        return False

    # 传输可能中断，落地的文件未必完整——校验通过才算数
    if not verify_dump(part):
        log(f'下载的 {name} 不完整，已丢弃')
        part.unlink(missing_ok=True)
        return False

    part.rename(final)
    log(f'取回 {name}（{final.stat().st_size / 1024 / 1024:.1f} MB）')
    return True


def main():
    parser = argparse.ArgumentParser(description='把服务器的数据库备份取回本机')
    parser.add_argument('--host', default=os.environ.get('BACKUP_SSH_HOST'),
                        help='服务器地址')
    parser.add_argument('--user', default=os.environ.get('BACKUP_SSH_USER', 'root'))
    parser.add_argument('--port', type=int,
                        default=int(os.environ.get('BACKUP_SSH_PORT', 22)))
    parser.add_argument('--remote-dir',
                        default=os.environ.get('BACKUP_REMOTE_DIR',
                                               '/var/www/MyTravelPanel/backups/db'))
    parser.add_argument('--dir', default=str(PROJECT_ROOT / 'backups' / 'db_server'))
    parser.add_argument('--keep', type=int, default=8)
    parser.add_argument('--identity', default=os.environ.get('BACKUP_SSH_KEY'))
    args = parser.parse_args()

    if not args.host:
        log('错误：未指定服务器地址，用 --host 或环境变量 BACKUP_SSH_HOST')
        return 2

    ssh, scp = find_tool('ssh'), find_tool('scp')
    if not ssh or not scp:
        log('错误：找不到 ssh / scp。Windows 可在「设置 > 应用 > 可选功能」装 OpenSSH 客户端')
        return 2

    target_dir = Path(args.dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    log(f'连接 {args.user}@{args.host}:{args.port} -> {args.remote_dir}')
    remote_names = list_remote(args, ssh)
    if remote_names is None:
        return 1
    if not remote_names:
        log('服务器上没有备份文件——先确认服务器的 cron 已经跑过')
        return 1

    have = {p.name for p in target_dir.iterdir() if p.is_file()}
    todo = sorted(n for n in remote_names if n not in have)
    log(f'服务器 {len(remote_names)} 份，本机已有 {len(remote_names) - len(todo)} 份，'
        f'需下载 {len(todo)} 份')

    failed = 0
    for name in todo:
        if not fetch(args, scp, name, target_dir):
            failed += 1

    # 本机侧也轮转，按库名分别保留
    for database in {n.rsplit('_', 2)[0] for n in remote_names}:
        rotate(target_dir, database, args.keep)

    if failed:
        log(f'结束：{failed} 份下载失败')
        return 1
    log('全部完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
