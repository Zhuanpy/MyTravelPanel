"""
项目文件管理路由
提供项目文件的上传、下载、删除等功能
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.projects.models.project import ProjectHeader, ProjectFile
from App_new.utils.decorators import staff_only
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

project_file = Blueprint('project_file', __name__, url_prefix='/file')

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                      'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z', 'txt', 'csv'}


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_project_files_path(header_id):
    """获取项目文件存储路径"""
    base_path = Path(os.getcwd()) / '资源' / 'Projects' / str(header_id)
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@project_file.route('/<int:header_id>/files', methods=['GET'])
@login_required
@staff_only
def get_files(header_id):
    """获取项目文件列表"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)
        files = ProjectFile.query.filter_by(header_id=header_id).order_by(ProjectFile.created_at.desc()).all()
        return jsonify({
            'success': True,
            'files': [f.to_dict() for f in files]
        })
    except Exception as e:
        current_app.logger.error(f"获取项目文件列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_file.route('/<int:header_id>/files/upload', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def upload_file(header_id):
    """上传项目文件"""
    try:
        header = ProjectHeader.query.get_or_404(header_id)

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400

        # 生成安全的存储文件名
        original_filename = secure_filename(file.filename) or file.filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        stored_filename = f"{uuid.uuid4().hex}{file_ext}"

        # 获取存储路径并保存文件
        file_path = get_project_files_path(header_id)
        full_path = file_path / stored_filename
        file.save(str(full_path))

        # 获取文件大小
        file_size = os.path.getsize(str(full_path))

        # 创建数据库记录
        project_file_record = ProjectFile(
            header_id=header_id,
            filename=file.filename,  # 保存原始文件名（含中文）
            stored_filename=stored_filename,
            file_path=str(full_path),
            file_size=file_size,
            file_type=file.content_type,
            description=request.form.get('description', ''),
            uploaded_by=current_user.username if hasattr(current_user, 'username') else current_user.email
        )

        db.session.add(project_file_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file': project_file_record.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"上传项目文件失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_file.route('/<int:header_id>/files/<int:file_id>/download', methods=['GET'])
@login_required
@staff_only
def download_file(header_id, file_id):
    """下载项目文件"""
    try:
        file_record = ProjectFile.query.filter_by(id=file_id, header_id=header_id).first_or_404()

        if not os.path.exists(file_record.file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404

        return send_file(
            file_record.file_path,
            as_attachment=True,
            download_name=file_record.filename
        )

    except Exception as e:
        current_app.logger.error(f"下载项目文件失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@project_file.route('/<int:header_id>/files/<int:file_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_file(header_id, file_id):
    """删除项目文件"""
    try:
        file_record = ProjectFile.query.filter_by(id=file_id, header_id=header_id).first_or_404()

        # 删除物理文件
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)

        # 删除数据库记录
        db.session.delete(file_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除项目文件失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
