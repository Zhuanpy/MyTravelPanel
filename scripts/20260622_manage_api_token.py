# -*- coding: utf-8 -*-
"""
API Token 管理：为用户创建 / 查看 / 撤销 API 访问令牌

令牌用于让 AI agent、脚本等非浏览器客户端以无状态方式访问受 @login_required
保护的接口，避免依赖浏览器 session 导致频繁掉线、反复登录。

请求时通过请求头携带令牌：
    X-API-Key: <token>
    或 Authorization: Bearer <token>

运行方式:
    python scripts/20260622_manage_api_token.py create <email> [名称]
    python scripts/20260622_manage_api_token.py list   <email>
    python scripts/20260622_manage_api_token.py revoke <token_id>

注意: 明文令牌只在创建时显示一次，请立即保存。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.auth.models import AuthUser, ApiToken


def _find_user(email):
    user = AuthUser.query.filter_by(email=email).first()
    if not user:
        print(f"❌ 未找到邮箱为 {email} 的用户")
        sys.exit(1)
    return user


def cmd_create(email, name='api-agent'):
    user = _find_user(email)
    token, raw_token = ApiToken.generate(user.id, name=name)
    db.session.add(token)
    db.session.commit()
    print("=" * 64)
    print("✅ 令牌已创建（明文仅显示这一次，请立即保存）")
    print("=" * 64)
    print(f"用户:   {user.username} <{user.email}>")
    print(f"名称:   {token.name}")
    print(f"令牌ID: {token.id}")
    print(f"令牌:   {raw_token}")
    print("-" * 64)
    print("调用示例:")
    print(f'  curl -H "X-API-Key: {raw_token}" https://你的域名/projects/list/')
    print("=" * 64)


def cmd_list(email):
    user = _find_user(email)
    tokens = ApiToken.query.filter_by(user_id=user.id).order_by(ApiToken.id).all()
    if not tokens:
        print(f"用户 {user.email} 当前没有任何令牌")
        return
    print(f"用户 {user.username} <{user.email}> 的令牌:")
    print("-" * 72)
    print(f"{'ID':<5}{'名称':<20}{'前缀':<16}{'启用':<6}{'最后使用'}")
    print("-" * 72)
    for t in tokens:
        last = t.last_used_at.strftime('%Y-%m-%d %H:%M') if t.last_used_at else '从未'
        print(f"{t.id:<5}{(t.name or ''):<20}{(t.prefix or ''):<16}{('是' if t.is_active else '否'):<6}{last}")
    print("-" * 72)


def cmd_revoke(token_id):
    token = ApiToken.query.get(int(token_id))
    if not token:
        print(f"❌ 未找到 ID 为 {token_id} 的令牌")
        sys.exit(1)
    token.is_active = False
    db.session.commit()
    print(f"✅ 令牌 #{token.id}（{token.name}）已撤销")


def main():
    args = sys.argv[1:]
    # server_update.sh 会用 --execute 跑所有 scripts/日期_*.py。
    # 本文件是令牌管理 CLI，不是数据库迁移，部署运行器调用时跳过，
    # 避免每次部署因缺 create/list/revoke 子命令而失败重试。
    if '--execute' in args:
        print("SKIP: 令牌管理 CLI，非数据库迁移，部署时不执行（用法见文件头）。")
        return
    if not args:
        print(__doc__)
        sys.exit(1)

    action = args[0]
    if action == 'create' and len(args) >= 2:
        cmd_create(args[1], args[2] if len(args) >= 3 else 'api-agent')
    elif action == 'list' and len(args) >= 2:
        cmd_list(args[1])
    elif action == 'revoke' and len(args) >= 2:
        cmd_revoke(args[1])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 确保 api_tokens 表存在（首次运行时自动创建）
        db.create_all()
        main()
