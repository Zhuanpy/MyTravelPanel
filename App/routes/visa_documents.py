from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..exts import db
from ..models import VisaDocuments, VisaTypes
from pathlib import Path
import logging

"""
签证文档管理 (visa_documents.py):
管理签证资料 (/visa/documents/manage_visas)
添加文档 (/visa/documents/add_document)
编辑文档 (/visa/documents/edit/<id>)
删除文档 (/visa/documents/delete/<id>)

"""
visa_documents = Blueprint('visa_documents', __name__)

@visa_documents.route('/manage_visas')
def manage_visas():
    visa_type = request.args.get('visa_type', '')
    identity = request.args.get('identity', '')

    # 查询所有签证类型列表供选择框使用
    visa_types = [type.visa_type for type in VisaTypes.query.order_by(VisaTypes.visa_type).all()]

    # 根据签证类型和身份过滤文档数据
    query = VisaDocuments.query
    if visa_type:
        query = query.filter_by(visa_type=visa_type)
    if identity:
        query = query.filter_by(singapore_identity=identity)
    
    documents = query.all()

    return render_template('visas/visa_document.html', 
                         documents=documents, 
                         visa_types=visa_types,
                         current_visa_type=visa_type)

@visa_documents.route('/add_document', methods=['GET', 'POST'])
def add_document():
    if request.method == 'GET':
        visa_type = request.args.get('visa_type', '')
        return render_template('visas/add_document.html', visa_type=visa_type)
        
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type = request.form.get('visa_type')
            singapore_identity = request.form.get('singapore_identity')
            document_info = request.form.get('document_info', '')
            additional_info = request.form.get('additional_info', '')

            # 数据验证
            if not all([visa_type, singapore_identity]):
                flash("签证类型和新加坡身份为必填字段", "error")
                return redirect(url_for('visa_documents.add_document', visa_type=visa_type))

            # 检查是否已存在相同签证类型和身份的记录
            existing = VisaDocuments.query.filter_by(
                visa_type=visa_type,
                singapore_identity=singapore_identity
            ).first()
            
            if existing:
                flash(f"已存在相同签证类型和身份的记录", "error")
                return redirect(url_for('visa_documents.add_document', visa_type=visa_type))

            # 创建新记录
            new_document = VisaDocuments(
                visa_type=visa_type,
                singapore_identity=singapore_identity,
                document_info=document_info,
                additional_info=additional_info
            )

            db.session.add(new_document)
            db.session.commit()
            flash("签证文档已添加", "success")
            return redirect(url_for('visa_documents.manage_visas', visa_type=visa_type))
            
        except Exception as e:
            db.session.rollback()
            flash(f"添加文档时出错：{str(e)}", "error")
            return redirect(url_for('visa_documents.add_document', visa_type=visa_type))

@visa_documents.route('/edit/<int:id>', methods=['GET'])
def edit_document(id):
    document = VisaDocuments.query.get_or_404(id)
    return render_template('visas/visa_document_edit.html', document=document)

@visa_documents.route('/update/<int:id>', methods=['POST'])
def update_document(id):
    document = VisaDocuments.query.get_or_404(id)
    
    try:
        document.document_info = request.form.get('document_info', '')
        document.additional_info = request.form.get('additional_info', '')
        
        db.session.commit()
        flash("文档更新成功", "success")
        return redirect(url_for('visa_documents.manage_visas', visa_type=document.visa_type))
        
    except Exception as e:
        db.session.rollback()
        flash(f"更新文档时出错：{str(e)}", "error")
        return redirect(url_for('visa_documents.edit_document', id=id))

@visa_documents.route('/delete/<int:id>', methods=['POST'])
def delete_document(id):
    document = VisaDocuments.query.get_or_404(id)
    visa_type = document.visa_type
    
    try:
        db.session.delete(document)
        db.session.commit()
        flash("文档删除成功", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"删除文档时出错：{str(e)}", "error")
    
    return redirect(url_for('visa_documents.manage_visas', visa_type=visa_type))


@visa_documents.route('/document_request/<visa_type>/<singapore_status>')
def display_document_request(visa_type, singapore_status):
    """
    从数据库中获取签证文件资料内容，并返回 JSON 格式的响应。

    参数:
    - visa_type (str): 签证类型
    - singapore_status (str): 新加坡身份状态

    返回:
    - dict: 包含签证文件资料内容的 JSON 响应
    """
    try:
        # 获取文档信息
        document_info = VisaDocuments.get_document_info(visa_type, singapore_status)

        return jsonify(document_info)
    except Exception as e:
        logging.error(f"获取签证文档时发生错误: {str(e)}")
        return jsonify({
            'document_info': '获取数据时发生错误',
            'additional_info': '获取数据时发生错误'
        }), 500


# @visa_documents.route('/visa/update_visa_documents')
# def update_visa_documents():
#     project_root = Path(__file__).resolve().parent.parent  # 获取项目的根目录路径
#     directory_path = project_root / "static" / "资源" / "签证"
#     identity_path = directory_path / "Z-模板"
#
#     # 检查主目录是否存在
#     if not directory_path.exists():
#         print("目录不存在")
#         return jsonify({"message": "签证资源目录不存在"}), 404
#
#     # 获取所有签证类型和身份模板文件夹名称
#     folder_names = [f.name for f in directory_path.iterdir() if f.is_dir() and f.name != "Z-模板"]
#     identitys = [f.name for f in identity_path.iterdir() if f.is_dir()]
#     identitys.remove("共用资料")
#     # 处理签证类型和身份模板数据
#     visa_info = {}
#
#     for visa_type in folder_names:
#         visa_info[visa_type] = identitys
#         # 打印身份模板名称
#         for singapore_identity in identitys:
#             print(singapore_identity)
#             existing_document = VisaDocuments.query.filter_by(visa_type=visa_type,
#                                                               singapore_identity=singapore_identity).first()
#
#             # 如果记录不存在则插入
#             if not existing_document:
#                 document_info = "待输入"
#                 additional_info = "待输入"
#                 VisaDocuments.insert_data(visa_type, singapore_identity, document_info, additional_info)
#
#             else:
#                 print(f"记录已存在，跳过插入：签证类型 - {visa_type}, 新加坡身份 - {singapore_identity}")
#
#     # 重定向到主页并输出签证类型和模板
#     return redirect(url_for("index.index"))


# @visa_documents.route('/visa/edit/<int:id>', methods=['GET'])
# def edit_visa(id):
#     document = VisaDocuments.query.get_or_404(id)
#     return render_template('visas/visa_document_edit.html', document=document)


# @visa_documents.route('/visa/update/<int:id>', methods=['GET', 'POST'])
# def update_visa(id):
#     document = VisaDocuments.query.get_or_404(id)
#
#     if request.method == 'POST':
#         try:
#             # 获取表单数据
#             visa_type = request.form.get('visa_type')
#             singapore_identity = request.form.get('singapore_identity')
#             document_info = request.form.get('document_info', '')
#             additional_info = request.form.get('additional_info', '')
#
#             # 数据验证
#             if not all([visa_type, singapore_identity]):
#                 flash("签证类型和新加坡身份为必填字段", "error")
#                 return redirect(url_for('visa_routes.edit_visa', id=id))
#
#             # 检查是否已存在相同签证类型和身份的记录（排除当前记录）
#             existing = VisaDocuments.query.filter(
#                 VisaDocuments.visa_type == visa_type,
#                 VisaDocuments.singapore_identity == singapore_identity,
#                 VisaDocuments.id != id
#             ).first()
#
#             if existing:
#                 flash(f"已存在相同签证类型和身份的记录", "error")
#                 return redirect(url_for('visa_routes.edit_visa', id=id))
#
#             # 更新记录
#             document.visa_type = visa_type
#             document.singapore_identity = singapore_identity
#             document.document_info = document_info
#             document.additional_info = additional_info
#
#             db.session.commit()
#             flash("签证记录已更新", "success")
#             return redirect(url_for('visa_routes.manage_visas', visa_type=visa_type))
#
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f"更新签证文档时发生错误: {str(e)}")
#             flash(f"更新失败: {str(e)}", "error")
#             return redirect(url_for('visa_routes.edit_visa', id=id))
#
#     return render_template('visas/visa_document_edit.html', document=document)
#

# @visa_documents.route('/add_document', methods=['GET', 'POST'])
# def add_document():
#     if request.method == 'GET':
#         visa_type = request.args.get('visa_type', '')
#         return render_template('visas/add_document.html', visa_type=visa_type)
#
#     if request.method == 'POST':
#         try:
#             # 获取表单数据
#             visa_type = request.form.get('visa_type')
#             singapore_identity = request.form.get('singapore_identity')
#             document_info = request.form.get('document_info', '')
#             additional_info = request.form.get('additional_info', '')
#
#             # 数据验证
#             if not all([visa_type, singapore_identity]):
#                 flash("签证类型和新加坡身份为必填字段", "error")
#                 return redirect(url_for('visa_routes.add_document', visa_type=visa_type))
#
#             # 检查是否已存在相同签证类型和身份的记录
#             existing = VisaDocuments.query.filter_by(
#                 visa_type=visa_type,
#                 singapore_identity=singapore_identity
#             ).first()
#
#             if existing:
#                 flash(f"已存在相同签证类型和身份的记录", "error")
#                 return redirect(url_for('visa_routes.add_document', visa_type=visa_type))
#
#             # 创建新记录
#             new_document = VisaDocuments(
#                 visa_type=visa_type,
#                 singapore_identity=singapore_identity,
#                 document_info=document_info,
#                 additional_info=additional_info
#             )
#
#             db.session.add(new_document)
#             db.session.commit()
#             flash("签证文档已添加", "success")
#             return redirect(url_for('visa_routes.manage_visas', visa_type=visa_type))
#
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f"添加签证文档时发生错误: {str(e)}")
#             flash(f"添加失败: {str(e)}", "error")
#             return redirect(url_for('visa_routes.add_document', visa_type=visa_type))
#
#     return render_template('visas/add_document.html')
