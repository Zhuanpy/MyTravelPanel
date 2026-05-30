# -*- coding: utf-8 -*-
"""
一键部署脚本：签证文档英文名称 + 资料清单重复清理

按顺序执行以下三步（依次调用已有脚本）：
  1) 20260530_add_name_en_to_documents_list.py   给 visa_documents_list 加 name_en 字段
  2) 20260530_translate_documents_name_en.py      用内置对照表填充英文名
  3) cleanup_doc_status_normalize.py --all         归并 "• " 前缀历史重复(保留已准备状态)

运行方式:
  python scripts/20260530_deploy_visa_doc_updates.py          # 执行全部三步
  python scripts/20260530_deploy_visa_doc_updates.py --dry    # 预览(不写库)
  python scripts/20260530_deploy_visa_doc_updates.py -y       # 跳过清理前的确认(非交互)

说明:
  - 第 1、2 步安全可重复执行(加字段有存在性检查，翻译默认只填空白)。
  - 第 3 步会归并/删除重复记录(已准备状态会保留)，执行前默认需确认，可用 -y 跳过。
"""
import sys
import os
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(script_name, extra_args=None):
    """以子进程方式运行同目录下的脚本，返回退出码。"""
    args = [sys.executable, os.path.join(SCRIPT_DIR, script_name)]
    if extra_args:
        args.extend(extra_args)
    # 强制子进程输出 UTF-8，避免 • 等字符报编码错
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    print("\n" + "=" * 70)
    print(">>> 运行: {} {}".format(script_name, ' '.join(extra_args or [])))
    print("=" * 70)
    result = subprocess.run(args, env=env)
    return result.returncode


def main():
    flags = set(sys.argv[1:])
    dry = '--dry' in flags
    skip_confirm = ('-y' in flags) or ('--yes' in flags)

    print("签证文档更新 一键部署 {}".format('[预览模式 DRY-RUN]' if dry else ''))

    # 第 1 步：加字段（dry 模式跳过，避免改表结构）
    if dry:
        print("\n[1/3] (dry) 跳过加字段迁移")
    else:
        code = run('20260530_add_name_en_to_documents_list.py')
        if code != 0:
            print("\n[中止] 第 1 步加字段失败，退出码 {}".format(code))
            return code

    # 第 2 步：填充英文名
    code = run('20260530_translate_documents_name_en.py', ['--dry'] if dry else None)
    if code != 0:
        print("\n[中止] 第 2 步填充英文名失败，退出码 {}".format(code))
        return code

    # 第 3 步：清理重复（破坏性，执行前确认）
    if dry:
        run('cleanup_doc_status_normalize.py')  # 不带参数=仅报告
    else:
        if not skip_confirm:
            ans = input("\n[3/3] 即将归并全部项目的重复资料(保留已准备状态)，确认执行? [y/N] ").strip().lower()
            if ans not in ('y', 'yes'):
                print("已跳过第 3 步清理。可稍后单独运行: "
                      "python scripts/cleanup_doc_status_normalize.py --all")
                print("\n部署完成(未执行清理)。")
                return 0
        code = run('cleanup_doc_status_normalize.py', ['--all'])
        if code != 0:
            print("\n[警告] 第 3 步清理失败，退出码 {}".format(code))
            return code

    print("\n" + "=" * 70)
    print("全部步骤完成 {}".format('(预览，未写库)' if dry else ''))
    print("=" * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
