#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加登录锁定相关字段的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def add_login_lock_fields():
    """添加登录锁定相关字段"""
    try:
        from App.exts import db
        from App import create_app
        
        app = create_app()
        
        with app.app_context():
            # 检查字段是否已存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('auth_users')]
            
            print("=== 检查现有字段 ===")
            print(f"现有字段: {columns}")
            
            # 需要添加的字段
            new_fields = [
                'login_attempts',
                'is_locked', 
                'locked_at',
                'unlock_at'
            ]
            
            missing_fields = [field for field in new_fields if field not in columns]
            
            if not missing_fields:
                print("✅ 所有字段已存在，无需迁移")
                return
            
            print(f"需要添加的字段: {missing_fields}")
            
            # 添加字段的SQL语句
            alter_statements = []
            
            if 'login_attempts' not in columns:
                alter_statements.append("ALTER TABLE auth_users ADD COLUMN login_attempts INT DEFAULT 0 COMMENT '登录失败次数'")
            
            if 'is_locked' not in columns:
                alter_statements.append("ALTER TABLE auth_users ADD COLUMN is_locked BOOLEAN DEFAULT FALSE COMMENT '账户是否被锁定'")
            
            if 'locked_at' not in columns:
                alter_statements.append("ALTER TABLE auth_users ADD COLUMN locked_at DATETIME NULL COMMENT '账户锁定时间'")
            
            if 'unlock_at' not in columns:
                alter_statements.append("ALTER TABLE auth_users ADD COLUMN unlock_at DATETIME NULL COMMENT '账户解锁时间'")
            
            print("\n=== SQL迁移语句 ===")
            for statement in alter_statements:
                print(statement + ";")
            
            print("\n=== 执行迁移 ===")
            print("请在MySQL中执行上述SQL语句来添加新字段")
            
            # 验证字段是否添加成功
            print("\n=== 验证字段 ===")
            try:
                # 重新检查字段
                inspector = db.inspect(db.engine)
                columns_after = [col['name'] for col in inspector.get_columns('auth_users')]
                print(f"迁移后字段: {columns_after}")
                
                # 检查新字段是否成功添加
                for field in new_fields:
                    if field in columns_after:
                        print(f"✅ {field} 字段添加成功")
                    else:
                        print(f"❌ {field} 字段添加失败")
                        
            except Exception as e:
                print(f"验证失败: {e}")
            
    except ImportError as e:
        print(f"错误: 无法导入必要的模块 - {e}")
        print("请确保在虚拟环境中运行此脚本")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    add_login_lock_fields()
