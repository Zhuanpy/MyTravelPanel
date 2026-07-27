# -*- coding: utf-8 -*-
"""
API Token 链路诊断：把一个明文 token 沿着真实认证路径走一遍，指出到底断在哪一步

背景:
    agent 报「token 失效」时，过去只能看到一个 302 到登录页的 HTML，无法区分
    「token 打错了」「token 被停用」「账号被禁用」「角色不是 staff」。
    本脚本直接对着数据库把 ApiToken.verify() 的每一步拆开报告。

注意:
    ApiToken 表里**不存明文**，只存 SHA256(token_hash)。所以不能用
    filter_by(token='mtp_...') 去查——没有 token 这个字段。
    本脚本按明文算哈希后精确匹配，找不到时再按 prefix 前缀给出近似提示。

运行方式:
    python scripts/tools/diagnose_api_token.py mtp_xxxxxxxx
    python scripts/tools/diagnose_api_token.py            # 不传则列出所有token概览
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.auth.models import AuthUser, ApiToken


def _line():
    print("-" * 66)


def overview():
    """列出所有 token 的状态概览（不泄露明文，只显示 prefix）"""
    tokens = ApiToken.query.order_by(ApiToken.id).all()
    if not tokens:
        print("❌ 库里一个 ApiToken 都没有。需要先创建：")
        print("   python scripts/20260622_manage_api_token.py create <邮箱> <标签>")
        return

    print(f"共 {len(tokens)} 个 token：\n")
    print(f"{'ID':<5}{'启用':<6}{'前缀':<16}{'名称':<16}{'用户':<26}{'最后使用'}")
    _line()
    for t in tokens:
        user = t.user
        who = f"{user.email}" if user else "(用户已删除)"
        role = user.role.name if (user and getattr(user, 'role', None)) else '?'
        last = t.last_used_at.strftime('%Y-%m-%d %H:%M') if t.last_used_at else '从未使用'
        flag = "✅" if t.is_active else "❌停用"
        print(f"{t.id:<5}{flag:<6}{(t.prefix or ''):<16}{t.name[:14]:<16}{who[:24]+'/'+role:<26}{last}")
    _line()
    print("\n要诊断具体某个 token：python scripts/tools/diagnose_api_token.py <明文token>")


def diagnose(raw_token):
    """按 ApiToken.verify() 的真实逻辑逐步检查"""
    print("=" * 66)
    print("API Token 链路诊断")
    print("=" * 66)
    print(f"待查 token: {raw_token[:12]}...（只显示前12位）")
    print(f"长度: {len(raw_token)}  前缀正确(mtp_): {'是' if raw_token.startswith('mtp_') else '否 ⚠️'}")
    _line()

    # 第1步：按哈希精确匹配
    print("\n[1/5] 按 SHA256 匹配数据库记录")
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = ApiToken.query.filter_by(token_hash=token_hash).first()

    if not token:
        print("  ❌ 库里没有这个 token（哈希对不上）")
        # 用 prefix 给近似提示：明文前12位是非机密的，创建时存了
        prefix = raw_token[:12]
        near = ApiToken.query.filter_by(prefix=prefix).all()
        if near:
            print(f"  ⚠️ 但有 {len(near)} 个 token 的 prefix 同为 {prefix}：")
            for t in near:
                print(f"     ID={t.id} 启用={t.is_active} 名称={t.name}")
            print("  → 说明 token 被截断/多了空格/复制漏字符，不是不存在。")
        else:
            print(f"  前缀 {prefix} 也没有任何记录 → token 完全是错的，或已被删除。")
        print("\n结论：重新生成一个 token。")
        print("  python scripts/20260622_manage_api_token.py create hemers@joyesc.com hermes")
        return

    print(f"  ✅ 命中记录 ID={token.id} 名称={token.name}")

    # 第2步：token 是否启用
    print("\n[2/5] token.is_active")
    if not token.is_active:
        print("  ❌ token 已被停用（is_active=False）→ verify() 直接返回 None")
        print("\n结论：这就是根因。重新生成 token，或把该行 is_active 改回 True。")
        return
    print("  ✅ 已启用")

    # 第3步：关联用户是否存在
    print("\n[3/5] 关联用户")
    user = token.user
    if not user:
        print(f"  ❌ user_id={token.user_id} 对应的账号不存在（已被删除）")
        print("\n结论：这就是根因。给现有账号重新生成 token。")
        return
    print(f"  ✅ {user.username} <{user.email}> (id={user.id})")

    # 第4步：用户是否启用（verify() 会检查）
    print("\n[4/5] user.is_active")
    if not user.is_active:
        print("  ❌ 账号被禁用 → verify() 返回 None，表现为 401")
        print("\n结论：这就是根因。启用该账号，或换一个可用账号的 token。")
        return
    print("  ✅ 账号正常")

    # 第5步：角色（@staff_only 要求）
    print("\n[5/5] 角色（@staff_only 要求 role == 'staff'）")
    role = user.role.name if getattr(user, 'role', None) else None
    if role != 'staff':
        print(f"  ❌ 当前角色是 {role!r}，不是 'staff'")
        print("     → token 本身有效（能过 login_required），但所有 @staff_only 接口返回 403。")
        print("\n结论：这就是根因。换 token 没用，要改账号角色。")
        return
    print(f"  ✅ role='staff'")

    _line()
    print("\n✅ 这个 token 在数据库层面完全正常，verify() 会成功返回用户。")
    print("\n如果实际请求仍然失败，说明问题不在 token 本身，而在传输环节：")
    print("  1) header 没真正发出去 —— Selenium 用 CDP Network.setExtraHTTPHeaders 注入，")
    print("     普通 driver.get() 不会带自定义 header。用 requests 则直接传 headers=。")
    print("  2) 请求被 301/302 跳转，跳转后 header 丢失（requests 默认不带自定义 header 跟随跨域跳转）。")
    print("  3) 打到了错误的域名/端口，或被 CDN/反代吃掉了 X-API-Key 头。")
    print("\n验证办法（在服务器上直连，绕开一切中间层）：")
    print(f'  curl -i -H "X-API-Key: {raw_token[:12]}..." http://127.0.0.1:5000/api/hermes/whoami')
    print("  200 = 链路通；401/403 = 按上面的返回体判断。")


def main():
    app = create_app()
    with app.app_context():
        if len(sys.argv) > 1:
            diagnose(sys.argv[1].strip())
        else:
            overview()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"诊断脚本出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
