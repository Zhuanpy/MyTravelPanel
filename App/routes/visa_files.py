from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from pathlib import Path
import os
import platform
import subprocess

"""
文件系统管理 (visa_files.py):
打开文件夹 (/visa/files/open_folder)
"""
visa_files = Blueprint('visa_files', __name__)

@visa_files.route('/open_folder')
def open_folder():
    """
    通用文件夹打开函数
    
    参数：
    - folder_type: 文件夹类型，可选值：project(项目文件夹)、visa_type(签证类型文件夹)、visa_root(签证根目录)
    - file_name: 文件夹名称，用于folder_type=project
    - visa_type: 签证类型，用于folder_type=visa_type
    - return_to: 打开后返回的页面，可选值：list(项目列表)、processing(签证处理)、home(首页)
    - visa_status, sort_by, filter_visa_type: 返回页面的状态参数
    """
    folder_type = request.args.get('folder_type', 'project')
    file_name = request.args.get('file_name', '')
    visa_type = request.args.get('visa_type', '')
    return_to = request.args.get('return_to', 'list')
    
    # 获取返回页面的状态参数
    visa_status = request.args.get('visa_status', 'all')
    sort_by = request.args.get('sort_by', 'name')
    filter_visa_type = request.args.get('filter_visa_type', 'all')
    
    # 获取项目根目录
    project_root = Path(__file__).resolve().parent.parent
    current_dir = Path.cwd()
    
    # 根据参数决定打开哪个文件夹
    if folder_type == 'project':
        base_folder = project_root / "static" / "资源" / "Project" / "Visa"
        folder_path = base_folder / file_name
        
        # 添加备选路径逻辑
        if not folder_path.exists() and visa_type:
            pre_folder_path = base_folder / visa_type / file_name
            if pre_folder_path.exists():
                folder_path = pre_folder_path
            else:
                error_msg = f"资源文件夹 {folder_path} 和备用文件夹 {pre_folder_path} 都不存在"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 404
                flash(error_msg, "error")
                if return_to == 'list':
                    return redirect(url_for("visa_project.show_current_all_projects",
                                            visa_status=visa_status,
                                            sort_by=sort_by,
                                            filter_visa_type=filter_visa_type))
                elif return_to == 'processing':
                    return redirect(url_for("visa_project.visa_processing", visa_type=visa_type))
                else:
                    return redirect(url_for("index.index"))
        elif not folder_path.exists():
            error_msg = f"资源文件夹 {folder_path} 不存在"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 404
            flash(error_msg, "error")
            if return_to == 'list':
                return redirect(url_for("visa_project.show_current_all_projects",
                                        visa_status=visa_status,
                                        sort_by=sort_by,
                                        filter_visa_type=filter_visa_type))
            elif return_to == 'processing':
                return redirect(url_for("visa_project.visa_processing", visa_type=visa_type))
            else:
                return redirect(url_for("index.index"))

    elif folder_type == 'visa_type':
        folder_path = current_dir / "App" / "static" / "资源" / "签证" / visa_type
        if not folder_path.exists():
            error_msg = f"资源文件夹 {folder_path} 不存在"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 404
            flash(error_msg, "error")
            return redirect(url_for("visa_project.visa_processing", visa_type=visa_type))

    elif folder_type == 'visa_root':
        folder_path = current_dir / "App" / "static" / "资源" / "签证"
        folder_path = os.path.join(folder_path)

    # 打开文件夹
    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other Unix-based systems
            subprocess.run(["xdg-open", folder_path])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '文件夹已打开'})
    except Exception as e:
        error_msg = f"无法打开文件夹: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, "error")

    # 根据参数决定重定向到哪个页面
    if return_to == 'list':
        return redirect(url_for("visa_project.show_current_all_projects",
                                visa_status=visa_status,
                                sort_by=sort_by,
                                filter_visa_type=filter_visa_type))
    elif return_to == 'processing':
        return redirect(url_for("visa_project.visa_processing", visa_type=visa_type))
    else:
        return redirect(url_for("index.index")) 