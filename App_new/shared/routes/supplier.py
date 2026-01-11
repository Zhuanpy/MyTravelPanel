# -*- coding: utf-8 -*-
"""
供应商路由 - 重定向到统一的公司管理页面
原供应商功能已合并到 /company/?role=supplier
"""

from flask import Blueprint, redirect, url_for, request

# 创建蓝图
supplier = Blueprint('supplier', __name__)


@supplier.route('/')
def suppliers():
    """供应商列表 -> 重定向到公司列表（供应商筛选）"""
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/supplier/<int:supplier_id>', methods=['GET'])
def view_supplier(supplier_id):
    """查看供应商 -> 重定向到公司详情"""
    # 需要通过映射表找到对应的 company_id
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.company_detail', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/add', methods=['GET', 'POST'])
def add_supplier():
    """添加供应商 -> 重定向到公司创建页面"""
    return redirect(url_for('corporate.create_company'))


@supplier.route('/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    """编辑供应商 -> 重定向到公司编辑页面"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.edit_company', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))


@supplier.route('/delete/<int:supplier_id>', methods=['GET', 'DELETE'])
def delete_supplier(supplier_id):
    """删除供应商 -> 重定向到公司删除"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.delete_company', company_id=company.id))
    return redirect(url_for('corporate.list_companies', role='supplier'))


# 以下路由保留原有功能（使用公司文件系统）

@supplier.route('/click/<int:supplier_id>', methods=['POST'])
def track_supplier_click(supplier_id):
    """追踪供应商点击 -> 使用公司点击接口"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.record_company_click', company_id=company.id), code=307)
    from flask import jsonify
    return jsonify({'success': False, 'message': '供应商不存在'})


@supplier.route('/open-folder/<int:supplier_id>', methods=['POST'])
def open_supplier_folder(supplier_id):
    """打开供应商本地文件夹"""
    from flask import jsonify
    from App_new.shared.models.Suppliers import get_supplier_by_id
    import os
    import subprocess
    import platform

    company = get_supplier_by_id(supplier_id)
    if not company:
        return jsonify({'success': False, 'message': '供应商不存在'})

    try:
        # 构建文件夹路径 - 使用公司路径
        base_path = r"E:\MyProject\MyTravelWork\MyTravelPanel\资源\Company"
        folder_path = os.path.join(base_path, str(company.id))

        # 确保文件夹存在
        os.makedirs(folder_path, exist_ok=True)

        # 根据操作系统打开文件夹
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(['explorer', folder_path])
        elif system == "Darwin":
            subprocess.Popen(['open', folder_path])
        elif system == "Linux":
            subprocess.Popen(['xdg-open', folder_path])

        return jsonify({
            'success': True,
            'message': f'已打开文件夹：{folder_path}',
            'folder_path': folder_path
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'打开文件夹失败：{str(e)}'
        })


@supplier.route('/upload-file/<int:supplier_id>', methods=['POST'])
def upload_supplier_file(supplier_id):
    """上传供应商文件 -> 使用公司文件接口"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.upload_file', company_id=company.id), code=307)
    from flask import jsonify
    return jsonify({'success': False, 'message': '供应商不存在'})


@supplier.route('/list-files/<int:supplier_id>', methods=['GET'])
def list_supplier_files(supplier_id):
    """获取供应商文件列表 -> 使用公司文件接口"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        return redirect(url_for('corporate.get_files', company_id=company.id))
    from flask import jsonify
    return jsonify({'success': False, 'message': '供应商不存在', 'files': []})


@supplier.route('/toggle-status/<int:supplier_id>', methods=['POST'])
def toggle_supplier_status(supplier_id):
    """切换供应商状态"""
    from flask import jsonify
    from App_new.exts import db
    from App_new.shared.models.Suppliers import get_supplier_by_id

    company = get_supplier_by_id(supplier_id)
    if not company:
        return jsonify({'success': False, 'message': '供应商不存在'})

    try:
        company.status = 'inactive' if company.status == 'active' else 'active'
        db.session.commit()
        return jsonify({
            'success': True,
            'status': company.status,
            'message': f'状态已更新为：{"活跃" if company.status == "active" else "非活跃"}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'状态更新失败：{str(e)}'
        })


@supplier.route('/download-file/<int:supplier_id>/<path:filename>', methods=['GET'])
def download_supplier_file(supplier_id, filename):
    """下载供应商文件"""
    from App_new.shared.models.Suppliers import get_supplier_by_id
    company = get_supplier_by_id(supplier_id)
    if company:
        # 查找文件并下载
        from App_new.business.projects.models.project import CompanyFile
        file_record = CompanyFile.query.filter_by(
            company_id=company.id,
            filename=filename
        ).first()
        if file_record:
            return redirect(url_for('corporate.download_file',
                                    company_id=company.id,
                                    file_id=file_record.id))
    from flask import jsonify
    return jsonify({'success': False, 'message': '文件不存在'}), 404


@supplier.route('/delete-file/<int:supplier_id>', methods=['POST'])
def delete_supplier_file(supplier_id):
    """删除供应商文件"""
    from flask import jsonify, request
    from App_new.shared.models.Suppliers import get_supplier_by_id

    company = get_supplier_by_id(supplier_id)
    if not company:
        return jsonify({'success': False, 'message': '供应商不存在'})

    filename = request.json.get('filename')
    if not filename:
        return jsonify({'success': False, 'message': '文件名不能为空'})

    # 查找文件并删除
    from App_new.business.projects.models.project import CompanyFile
    file_record = CompanyFile.query.filter_by(
        company_id=company.id,
        filename=filename
    ).first()

    if file_record:
        return redirect(url_for('corporate.delete_file',
                                company_id=company.id,
                                file_id=file_record.id), code=307)

    return jsonify({'success': False, 'message': '文件不存在'})
