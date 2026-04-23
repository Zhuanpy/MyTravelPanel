# -*- coding: utf-8 -*-
"""
慢请求/慢 SQL 日志分析脚本

按 endpoint 或 SQL 模式聚合，输出 TOP N，帮助快速定位 CPU 热点。

用法：
    python scripts/analyze_perf_logs.py                    # 默认：两类都分析，TOP 20
    python scripts/analyze_perf_logs.py --top 10           # TOP 10
    python scripts/analyze_perf_logs.py --type request     # 只看慢请求
    python scripts/analyze_perf_logs.py --type query       # 只看慢 SQL
    python scripts/analyze_perf_logs.py --sort count       # 按次数排序（默认按总耗时）
    python scripts/analyze_perf_logs.py --days 1           # 只看最近 1 天
    python scripts/analyze_perf_logs.py --log-dir /path    # 指定日志目录

排序键：
    total（默认）= 总耗时（最影响整体性能）
    count        = 出现次数（最频繁）
    avg          = 平均耗时（最慢的单次请求）
    max          = 最大单次耗时
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta


# 日志行格式：
#   2026-04-18 15:01:28 | slow_request method=GET path=/foo endpoint=bp.view status=200 elapsed=1234.5ms ...
#   2026-04-18 15:01:28 | slow_sql elapsed=600.0ms path=/foo user=... | sql=SELECT ... | params=...

REQUEST_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| slow_request '
    r'method=(?P<method>\S+) path=(?P<path>\S+) endpoint=(?P<endpoint>\S+) '
    r'status=(?P<status>\d+) elapsed=(?P<elapsed>[\d.]+)ms '
    r'query_count=(?P<qcount>\d+) query_total=(?P<qtotal>[\d.]+)ms '
    r'slow_query_count=(?P<slowqcount>\d+) (?P<userpart>.*)$'
)

QUERY_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| slow_sql '
    r'elapsed=(?P<elapsed>[\d.]+)ms path=(?P<path>\S+) (?P<user>\S+) \| '
    r'sql=(?P<sql>.*?) \| params=(?P<params>.*)$'
)

# SQL 归一化：把字面量替换为占位符，便于聚合相同模式的不同参数
SQL_NUMBER_RE = re.compile(r"\b\d+\.?\d*\b")
SQL_STRING_RE = re.compile(r"'[^']*'")
SQL_IN_LIST_RE = re.compile(r"IN\s*\([^)]*\)", re.IGNORECASE)


def normalize_sql(sql: str) -> str:
    """归一化 SQL，把数字/字符串/IN 列表替换为占位符"""
    s = SQL_IN_LIST_RE.sub("IN (?)", sql)
    s = SQL_STRING_RE.sub("?", s)
    s = SQL_NUMBER_RE.sub("?", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:200]  # 限制长度便于显示


def parse_log_file(path: str, line_re, since: datetime | None):
    """逐行解析日志，yield 匹配的字典"""
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = line_re.match(line)
            if not m:
                continue
            data = m.groupdict()
            if since:
                try:
                    ts = datetime.strptime(data['ts'], '%Y-%m-%d %H:%M:%S')
                    if ts < since:
                        continue
                except ValueError:
                    pass
            yield data


def analyze_requests(log_dir: str, since: datetime | None, top: int, sort_key: str):
    """聚合慢请求 by endpoint"""
    path = os.path.join(log_dir, 'slow_request.log')
    if not os.path.exists(path):
        print(f"[!] 找不到慢请求日志：{path}")
        return

    # 同时解析所有归档文件（slow_request.log.1 等）
    files = [path] + [f"{path}.{i}" for i in range(1, 6) if os.path.exists(f"{path}.{i}")]

    # endpoint -> {count, total_ms, max_ms, paths(set), q_total_ms}
    stats = defaultdict(lambda: {
        'count': 0, 'total_ms': 0.0, 'max_ms': 0.0,
        'q_total_ms': 0.0, 'q_count_total': 0,
        'paths': set(), 'sample_method': '',
    })

    total_records = 0
    for f in files:
        for d in parse_log_file(f, REQUEST_RE, since):
            total_records += 1
            ep = d['endpoint']
            elapsed = float(d['elapsed'])
            s = stats[ep]
            s['count'] += 1
            s['total_ms'] += elapsed
            s['max_ms'] = max(s['max_ms'], elapsed)
            s['q_total_ms'] += float(d['qtotal'])
            s['q_count_total'] += int(d['qcount'])
            s['paths'].add(d['path'])
            s['sample_method'] = d['method']

    if total_records == 0:
        print("[i] 没有慢请求记录（或时间范围内无数据）")
        return

    # 排序
    def keyfunc(item):
        _, s = item
        return {
            'total': s['total_ms'],
            'count': s['count'],
            'avg': s['total_ms'] / s['count'],
            'max': s['max_ms'],
        }.get(sort_key, s['total_ms'])

    items = sorted(stats.items(), key=keyfunc, reverse=True)[:top]

    print(f"\n{'='*100}")
    print(f"慢请求 TOP {top} （共 {total_records} 条记录，按 {sort_key} 排序）")
    print(f"{'='*100}")
    print(f"{'endpoint':<40} {'次数':>6} {'总耗时(ms)':>12} {'平均(ms)':>10} {'最大(ms)':>10} {'SQL均次':>8}")
    print('-' * 100)
    for ep, s in items:
        avg = s['total_ms'] / s['count']
        avg_q = s['q_count_total'] / s['count']
        print(f"{ep[:40]:<40} {s['count']:>6} {s['total_ms']:>12.1f} {avg:>10.1f} {s['max_ms']:>10.1f} {avg_q:>8.1f}")

    # 显示每个 TOP endpoint 的代表性 path（前 3 个）
    print(f"\n{'-'*100}")
    print("各 endpoint 的代表性 path：")
    for ep, s in items[:10]:
        sample_paths = sorted(s['paths'])[:3]
        more = f" (+{len(s['paths'])-3})" if len(s['paths']) > 3 else ''
        print(f"  {ep}: {' | '.join(sample_paths)}{more}")


def analyze_queries(log_dir: str, since: datetime | None, top: int, sort_key: str):
    """聚合慢 SQL by 归一化模式"""
    path = os.path.join(log_dir, 'slow_query.log')
    if not os.path.exists(path):
        print(f"[!] 找不到慢 SQL 日志：{path}")
        return

    files = [path] + [f"{path}.{i}" for i in range(1, 6) if os.path.exists(f"{path}.{i}")]

    # normalized_sql -> {count, total_ms, max_ms, paths(Counter), example}
    stats = defaultdict(lambda: {
        'count': 0, 'total_ms': 0.0, 'max_ms': 0.0,
        'paths': defaultdict(int), 'example': '',
    })

    total_records = 0
    for f in files:
        for d in parse_log_file(f, QUERY_RE, since):
            total_records += 1
            normalized = normalize_sql(d['sql'])
            elapsed = float(d['elapsed'])
            s = stats[normalized]
            s['count'] += 1
            s['total_ms'] += elapsed
            s['max_ms'] = max(s['max_ms'], elapsed)
            s['paths'][d['path']] += 1
            if not s['example']:
                s['example'] = d['sql'][:300]

    if total_records == 0:
        print("[i] 没有慢 SQL 记录（或时间范围内无数据）")
        return

    def keyfunc(item):
        _, s = item
        return {
            'total': s['total_ms'],
            'count': s['count'],
            'avg': s['total_ms'] / s['count'],
            'max': s['max_ms'],
        }.get(sort_key, s['total_ms'])

    items = sorted(stats.items(), key=keyfunc, reverse=True)[:top]

    print(f"\n{'='*100}")
    print(f"慢 SQL TOP {top} （共 {total_records} 条记录，按 {sort_key} 排序）")
    print(f"{'='*100}")
    for i, (norm_sql, s) in enumerate(items, 1):
        avg = s['total_ms'] / s['count']
        top_path = sorted(s['paths'].items(), key=lambda x: -x[1])[0]
        print(f"\n[{i}] 次数={s['count']} 总耗时={s['total_ms']:.1f}ms 平均={avg:.1f}ms 最大={s['max_ms']:.1f}ms")
        print(f"    最常出现于：{top_path[0]} ({top_path[1]} 次)")
        print(f"    SQL：{norm_sql}")


def main():
    parser = argparse.ArgumentParser(description='分析慢请求/慢 SQL 日志')
    parser.add_argument('--top', type=int, default=20, help='显示 TOP N（默认 20）')
    parser.add_argument('--type', choices=['request', 'query', 'both'], default='both',
                        help='分析类型（默认 both）')
    parser.add_argument('--sort', choices=['total', 'count', 'avg', 'max'], default='total',
                        help='排序键（默认 total）')
    parser.add_argument('--days', type=int, default=0, help='只分析最近 N 天的数据（默认全部）')
    parser.add_argument('--log-dir', default=None, help='日志目录（默认项目 logs/）')
    args = parser.parse_args()

    log_dir = args.log_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
    )
    if not os.path.isdir(log_dir):
        print(f"[!] 日志目录不存在：{log_dir}", file=sys.stderr)
        sys.exit(1)

    since = datetime.now() - timedelta(days=args.days) if args.days > 0 else None
    if since:
        print(f"[i] 时间范围：{since.strftime('%Y-%m-%d %H:%M:%S')} 之后")
    print(f"[i] 日志目录：{log_dir}")

    if args.type in ('request', 'both'):
        analyze_requests(log_dir, since, args.top, args.sort)
    if args.type in ('query', 'both'):
        analyze_queries(log_dir, since, args.top, args.sort)


if __name__ == '__main__':
    main()
