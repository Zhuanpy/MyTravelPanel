# -*- coding: utf-8 -*-
"""
重置员工/用户登录密码

用于管理员在服务器端为忘记密码的账号直接设置新密码，
同时清除登录失败锁定状态（is_locked / login_attempts / unlock_at），
并递增 session_version 使该用户其它已登录会话立即失效。

运行方式:
    python scripts/20260706_reset_user_password.py <email> <新密码>
    python scripts/20260706_reset_user_password.py <email>            # 不给密码则随机生成一个

示例:
    python scripts/20260706_reset_user_password.py hermes@joyesc.com NewPass123
"""

import sys
import os
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.auth.models import AuthUser


def reset_password(email, new_password=None):
    user = AuthUser.query.filter_by(email=email).first()
    if not user:
        print(f"❌ 未找到邮箱为 {email} 的用户")
        sys.exit(1)

    # 未指定密码则生成一个便于临时登录的随机密码
    if not new_password:
        new_password = 'mtp_' + secrets.token_urlsafe(9)

    # 设置新密码（默认递增 session_version，强制其它会话失效）
    user.set_password(new_password)

    # 清除登录失败锁定状态，确保重置后能立即登录
    user.login_attempts = 0
    user.is_locked = False
    user.locked_at = None
    user.unlock_at = None

    db.session.commit()

    print("=" * 60)
    print("✅ 密码已重置")
    print("=" * 60)
    print(f"用户:   {user.username} <{user.email}>")
    print(f"新密码: {new_password}")
    print("-" * 60)
    print("请立即用新密码登录，并在登录后自行修改为常用密码。")
    print("=" * 60)


def main():
    args = sys.argv[1:]
    # server_update.sh 会用 --execute 跑所有 scripts/日期_*.py。
    # 本文件是密码重置 CLI，不是数据库迁移，部署运行器调用时跳过，
    # 避免每次部署因缺 email 参数而失败重试。
    if '--execute' in args:
        print("SKIP: 密码重置 CLI，非数据库迁移，部署时不执行（用法见文件头）。")
        return
    if not args:
        print(__doc__)
        sys.exit(1)

    email = args[0]
    new_password = args[1] if len(args) >= 2 else None
    reset_password(email, new_password)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()
