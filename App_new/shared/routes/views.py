from flask import Blueprint, render_template, jsonify, send_from_directory
import os
from pathlib import Path

# 创建共享模块的蓝图
dex = Blueprint("shared", __name__)

@dex.route('/portal')
def portal():
    """统一入口门户页面"""
    return render_template('portal.html')

@dex.route('/')
def index():
    """网站首页 - 显示门户页面"""
    return render_template('portal.html')

@dex.route('/legacy-home')
def legacy_home():
    """原来的首页功能 - 待迁移"""
    # TODO: 迁移旧的首页功能到新架构
    return render_template('portal.html')

# 注意：/public/* 路径已经由 guest 蓝图处理，这里不需要重复定义路由

# 为了兼容性，添加重定向路由到正确的认证页面
@dex.route('/auth/staff_login')
def auth_staff_login_redirect():
    """员工登录页面重定向"""
    from flask import redirect, url_for
    return redirect(url_for('auth.staff_login'))

@dex.route('/auth/member_login')
def auth_member_login_redirect():
    """会员登录页面重定向"""
    from flask import redirect, url_for
    return redirect(url_for('auth.member_login'))

@dex.route('/auth/admin_login')
def auth_admin_login_redirect():
    """管理员登录页面重定向"""
    from flask import redirect, url_for
    return redirect(url_for('auth.admin_login'))

@dex.route('/open_package_folder', methods=['GET', 'POST'])
def open_package_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "旅游产品"
    folder_path = os.path.join(folder_path)
    # 使用 explorer 命令确保文件夹置顶显示
    import subprocess
    subprocess.run(['explorer', str(folder_path)], shell=True)
    # 返回JSON响应，表示成功操作
    return jsonify({"status": "success"})


@dex.route('/open_package_project_folder', methods=['GET', 'POST'])
def open_package_project_folder():
    current_dir = Path.cwd()
    from App.config import Config
    folder_path = Config.TOUR_PROJECTS_PATH
    folder_path = os.path.join(folder_path)
    # 使用 explorer 命令确保文件夹置顶显示
    import subprocess
    subprocess.run(['explorer', str(folder_path)], shell=True)
    return jsonify({"status": "success"})


@dex.route('/open_bill_project_folder', methods=['GET', 'POST'])
def open_bill_project_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "账单"
    folder_path = os.path.join(folder_path)
    # 使用 explorer 命令确保文件夹置顶显示
    import subprocess
    subprocess.run(['explorer', str(folder_path)], shell=True)
    return jsonify({"status": "success"})


@dex.route('/add_visa_information', methods=['POST'])
def add_visa_information():
    # Logic to edit the city would go here
    pass


@dex.route('/resource/<path:filename>')
def resource_file(filename):
    import os
    from pathlib import Path
    base_dir = Path.cwd() / '资源' / '旅游产品'
    # 安全性校验，防止路径穿越
    safe_path = os.path.normpath(os.path.join(base_dir, filename))
    if not safe_path.startswith(str(base_dir)):
        return '非法路径', 403
    return send_from_directory(base_dir, filename)

