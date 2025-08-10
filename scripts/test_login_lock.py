#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试登录锁定功能的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_login_lock_functionality():
    """测试登录锁定功能"""
    try:
        from App.exts import db
        from App.models.auth import AuthUser
        from App import create_app
        
        app = create_app()
        
        with app.app_context():
            print("=== 测试登录锁定功能 ===")
            
            # 查找测试用户
            test_user = AuthUser.query.filter_by(email='staff@mytravelpanel.com').first()
            
            if not test_user:
                print("❌ 未找到测试用户 staff@mytravelpanel.com")
                return
            
            print(f"✅ 找到测试用户: {test_user.username}")
            print(f"   当前状态: {'已锁定' if test_user.is_locked else '未锁定'}")
            print(f"   登录失败次数: {test_user.login_attempts}")
            
            # 测试记录登录失败
            print("\n=== 测试记录登录失败 ===")
            original_attempts = test_user.login_attempts
            test_user.record_login_failure()
            print(f"   失败次数从 {original_attempts} 增加到 {test_user.login_attempts}")
            
            if test_user.login_attempts >= 5:
                print(f"   ✅ 账户已自动锁定: {test_user.is_locked}")
                print(f"   锁定时间: {test_user.locked_at}")
                print(f"   预计解锁时间: {test_user.unlock_at}")
                
                # 测试检查锁定状态
                is_locked = test_user.is_account_locked()
                print(f"   账户锁定检查: {'是' if is_locked else '否'}")
                
                # 测试获取剩余锁定时间
                remaining_time = test_user.get_remaining_lock_time()
                print(f"   剩余锁定时间: {remaining_time} 分钟")
                
                # 测试解锁账户
                print("\n=== 测试解锁账户 ===")
                test_user.unlock_account()
                print(f"   ✅ 账户已解锁: {not test_user.is_locked}")
                print(f"   失败次数已重置: {test_user.login_attempts}")
            else:
                print(f"   ℹ️  账户未锁定，还需 {5 - test_user.login_attempts} 次失败才会锁定")
            
            # 测试记录登录成功
            print("\n=== 测试记录登录成功 ===")
            test_user.record_login_success()
            print(f"   ✅ 登录成功记录完成")
            print(f"   失败次数重置为: {test_user.login_attempts}")
            print(f"   锁定状态: {test_user.is_locked}")
            
            # 验证数据库更新
            db.session.commit()
            print("\n=== 数据库更新验证 ===")
            
            # 重新查询用户
            updated_user = AuthUser.query.get(test_user.id)
            print(f"   数据库中的失败次数: {updated_user.login_attempts}")
            print(f"   数据库中的锁定状态: {updated_user.is_locked}")
            
            print("\n✅ 登录锁定功能测试完成！")
            
    except ImportError as e:
        print(f"错误: 无法导入必要的模块 - {e}")
        print("请确保在虚拟环境中运行此脚本")
    except Exception as e:
        print(f"错误: {e}")

def show_user_lock_status():
    """显示所有用户的锁定状态"""
    try:
        from App.exts import db
        from App.models.auth import AuthUser
        from App import create_app
        
        app = create_app()
        
        with app.app_context():
            print("=== 用户锁定状态概览 ===")
            
            users = AuthUser.query.all()
            
            if not users:
                print("❌ 没有找到任何用户")
                return
            
            print(f"总用户数: {len(users)}")
            print()
            
            locked_users = []
            high_attempt_users = []
            
            for user in users:
                if user.is_locked:
                    locked_users.append(user)
                elif user.login_attempts > 0:
                    high_attempt_users.append(user)
                
                print(f"用户: {user.username} ({user.email})")
                print(f"  角色: {user.role.name if user.role else '未知'}")
                print(f"  状态: {'🔒 已锁定' if user.is_locked else '✅ 正常'}")
                print(f"  失败次数: {user.login_attempts}/5")
                
                if user.is_locked:
                    remaining = user.get_remaining_lock_time()
                    print(f"  剩余锁定时间: {remaining} 分钟")
                
                print()
            
            print("=== 统计信息 ===")
            print(f"🔒 已锁定用户: {len(locked_users)}")
            print(f"⚠️  高失败次数用户: {len(high_attempt_users)}")
            print(f"✅ 正常用户: {len(users) - len(locked_users) - len(high_attempt_users)}")
            
    except ImportError as e:
        print(f"错误: 无法导入必要的模块 - {e}")
        print("请确保在虚拟环境中运行此脚本")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("选择测试选项:")
    print("1. 测试登录锁定功能")
    print("2. 显示用户锁定状态")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        test_login_lock_functionality()
    elif choice == "2":
        show_user_lock_status()
    else:
        print("无效选择，运行默认测试...")
        test_login_lock_functionality()
