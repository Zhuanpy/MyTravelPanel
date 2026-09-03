#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
数据库定期备份

在服务器上跑 mysqldump 导出全库、gzip 压缩、按份数轮转。
设计成不依赖 Flask 应用：应用挂了、代码改坏了，备份照样能跑。

放在 scripts/tools/ 而不是 scripts/ 是刻意的——部署脚本会执行 scripts/ 下
所有日期开头的文件，备份脚本不该在每次部署时被当成迁移跑一遍。

备份就地存放：在服务器上跑就存服务器，在本机跑就存本机，两边互不相干。
凭据一律从各自的 .env 读，脚本里不写任何密码。

用法:
    # 服务器
    cd /var/www/MyTravelPanel && venv/bin/python scripts/tools/db_backup.py
    # 本机 Windows
    python scripts/tools/db_backup.py

    --dir        备份存放目录，默认 <项目根>/backups/db
    --keep       每个库保留最近几份，默认 8（每周一次≈两个月）
    --databases  要备份的库，默认取 .env 里的 DB_NAME 和 DB_NAME_DATA
    --mysqldump  mysqldump 路径，默认自动找（Windows 会去 Workbench 目录找）

退出码 0 成功，非 0 失败——cron 里可据此报警。
配置了但不存在的库按"跳过"处理，不算失败：本地和服务器的库不一定一样。

恢复（重要，别等出事才第一次看）:
    # Linux
    gunzip -c backups/db/travelindustry_20260903_030000.sql.gz | \
        mysql -u root -p travelindustry

    # Windows（mysql.exe 在 Workbench 目录里）
    python -c "import gzip,sys; sys.stdout.buffer.write(gzip.open(r'backups\db\xxx.sql.gz','rb').read())" | ^
        "C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe" -u root -p travelindustry

    恢复是覆盖式的，动手前先把当前库另存一份。
    建议先恢复到一个临时库（CREATE DATABASE restore_test）核对无误再动正式库。

详见 docs/数据库备份.md
"""

import argparse
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# mysqldump 正常结束时会在文件末尾写这行。用它判断导出是否完整——
# 磁盘写满或进程被杀时，文件是存在的但内容被截断，只看返回码会漏判。
DUMP_END_MARKER = 'Dump completed'


# Windows 上 mysqldump 通常不在 PATH 里，装 Workbench / Server 时会带一份
WINDOWS_MYSQLDUMP_GLOBS = (
    r'C:\Program Files\MySQL\MySQL Workbench *\mysqldump.exe',
    r'C:\Program Files\MySQL\MySQL Server *\bin\mysqldump.exe',
    r'C:\Program Files (x86)\MySQL\MySQL Server *\bin\mysqldump.exe',
    r'C:\xampp\mysql\bin\mysqldump.exe',
)


def log(message):
    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}', flush=True)


def find_mysqldump(explicit=None):
    """定位 mysqldump 可执行文件，找不到返回 None"""
    if explicit:
        return explicit if Path(explicit).exists() else None

    found = shutil.which('mysqldump')
    if found:
        return found

    if os.name == 'nt':
        import glob
        for pattern in WINDOWS_MYSQLDUMP_GLOBS:
            matches = sorted(glob.glob(pattern), reverse=True)   # 版本号大的优先
            if matches:
                return matches[0]
    return None


def load_env():
    """读取项目根目录的 .env，已存在的环境变量优先（systemd 注入的不被覆盖）"""
    env_file = PROJECT_ROOT / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def db_settings():
    load_env()
    password = os.environ.get('DB_PASSWORD', '')
    if not password:
        log('错误：DB_PASSWORD 未设置，检查 .env 或 systemd EnvironmentFile')
        sys.exit(2)
    return {
        'user': os.environ.get('DB_USER', 'root'),
        'password': password,
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'port': os.environ.get('DB_PORT', '3306'),
    }


def default_databases():
    load_env()
    names = [os.environ.get('DB_NAME', 'travelindustry'),
             os.environ.get('DB_NAME_DATA', '')]
    # 去空去重，保持顺序
    seen, out = set(), []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def write_defaults_file(settings):
    """把密码写进临时配置文件交给 mysqldump

    不能用 mysqldump -p<密码>：命令行参数在 ps / /proc 里对同机所有用户可见，
    等于把数据库密码广播出去。--defaults-extra-file 是官方推荐的做法。
    """
    handle = tempfile.NamedTemporaryFile('w', suffix='.cnf', delete=False,
                                         encoding='utf-8')
    os.chmod(handle.name, 0o600)      # 只有当前用户可读
    handle.write(
        '[client]\n'
        f'user={settings["user"]}\n'
        f'password={settings["password"]}\n'
        f'host={settings["host"]}\n'
        f'port={settings["port"]}\n'
    )
    handle.close()
    return handle.name


def dump_database(database, settings, target_dir, mysqldump):
    """导出单个库到 <库名>_<时间戳>.sql.gz，返回文件路径；失败返回 None"""
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_path = target_dir / f'{database}_{stamp}.sql.gz'
    # 先写 .part，完整校验通过后再改名。中途失败不会留下一个看着像成功的文件。
    part_path = final_path.with_suffix('.gz.part')

    defaults_file = write_defaults_file(settings)
    try:
        command = [
            mysqldump,
            f'--defaults-extra-file={defaults_file}',
            '--single-transaction',   # InnoDB 一致性快照，不锁表，线上可跑
            '--quick',                # 逐行取，不把整表读进内存
            '--routines',             # 存储过程和函数
            '--triggers',
            '--events',
            '--default-character-set=utf8mb4',
            '--hex-blob',             # 二进制字段安全
            database,
        ]
        log(f'导出 {database} ...')
        with gzip.open(part_path, 'wb') as out:
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            shutil.copyfileobj(process.stdout, out)
            process.stdout.close()
            stderr = process.stderr.read().decode('utf-8', 'replace')
            process.stderr.close()
            code = process.wait()

        if code != 0:
            part_path.unlink(missing_ok=True)
            # 1049 = 库不存在。本地和服务器的库不一定一样（比如 traveldata 只在
            # 服务器上有），这种情况当"跳过"处理，不然每周都报失败，告警就没人看了
            if 'error: 1049' in stderr or 'Unknown database' in stderr:
                log(f'跳过 {database}：库不存在')
                return 'skipped'
            log(f'失败：mysqldump 退出码 {code}\n{stderr.strip()}')
            return None

        if not verify_dump(part_path):
            log(f'失败：{database} 的导出文件不完整（缺少结束标记），已丢弃')
            part_path.unlink(missing_ok=True)
            return None

        part_path.rename(final_path)
        size_mb = final_path.stat().st_size / 1024 / 1024
        log(f'完成 {final_path.name}（{size_mb:.1f} MB）')
        return final_path

    finally:
        os.unlink(defaults_file)


def verify_dump(path):
    """检查压缩包能否解压、且末尾有 mysqldump 的结束标记

    只看 mysqldump 返回码不够：磁盘写满、进程被 OOM kill 时，
    文件存在但内容截断，恢复时才发现就晚了。
    """
    try:
        tail = b''
        with gzip.open(path, 'rb') as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b''):
                tail = (tail + chunk)[-4096:]
        return DUMP_END_MARKER.encode() in tail
    # 截断的 gzip 抛的是 EOFError，它不是 OSError 的子类——只捕 OSError 会让
    # 脚本在"传输中断"这个最该被识破的场景直接崩掉。zlib.error 同理。
    except (OSError, EOFError, zlib.error) as exc:
        log(f'校验失败：{exc}')
        return False


def rotate(target_dir, database, keep):
    """只保留最近 keep 份，多余的删掉——不然磁盘迟早被写满"""
    pattern = re.compile(rf'^{re.escape(database)}_\d{{8}}_\d{{6}}\.sql\.gz$')
    files = sorted((p for p in target_dir.iterdir() if pattern.match(p.name)),
                   key=lambda p: p.name, reverse=True)
    for old in files[keep:]:
        old.unlink()
        log(f'清理旧备份 {old.name}')


def main():
    parser = argparse.ArgumentParser(description='数据库备份')
    parser.add_argument('--dir', default=str(PROJECT_ROOT / 'backups' / 'db'),
                        help='备份存放目录')
    parser.add_argument('--keep', type=int, default=8,
                        help='每个库保留最近几份，默认 8')
    parser.add_argument('--databases', nargs='*',
                        help='要备份的库名，默认取 .env 里的 DB_NAME / DB_NAME_DATA')
    parser.add_argument('--mysqldump', default=os.environ.get('MYSQLDUMP_PATH'),
                        help='mysqldump 可执行文件路径，默认自动查找')
    args = parser.parse_args()

    mysqldump = find_mysqldump(args.mysqldump)
    if not mysqldump:
        log('错误：找不到 mysqldump。Linux 装 mysql-client；'
            'Windows 装了 MySQL Workbench 就自带，或用 --mysqldump 指定完整路径')
        return 2
    log(f'使用 {mysqldump}')

    target_dir = Path(args.dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    databases = args.databases or default_databases()
    if not databases:
        log('错误：没有可备份的库')
        return 2

    settings = db_settings()
    log(f'开始备份：{", ".join(databases)} -> {target_dir}')

    failed, done, skipped = [], [], []
    for database in databases:
        result = dump_database(database, settings, target_dir, mysqldump)
        if result == 'skipped':
            skipped.append(database)
        elif result:
            done.append(database)
            rotate(target_dir, database, args.keep)
        else:
            failed.append(database)

    summary = f'完成 {len(done)} 个'
    if skipped:
        summary += f'，跳过 {len(skipped)} 个（{", ".join(skipped)}）'
    if failed:
        log(f'{summary}，失败 {len(failed)} 个 -> {", ".join(failed)}')
        return 1
    if not done:
        log(f'{summary}，没有任何库被备份')
        return 1

    log(summary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
