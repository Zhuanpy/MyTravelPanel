from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..exts import db
from ..models import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaCountries
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

@visa_documents.route('/manage_visas', methods=['GET', 'POST'])
def manage_visas():
    if request.method == 'POST':
        try:
            document_id = request.form.get('document_id')
            document = VisaDocuments.query.get_or_404(document_id)
            
            # 更新文档信息
            document.singapore_identity = request.form.get('singapore_identity')
            document.document_info = request.form.get('document_info', '')
            document.additional_info = request.form.get('additional_info', '')
            
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': '文档更新成功'
                })
            
            flash("文档更新成功", "success")
            return redirect(url_for('visa_documents.manage_visas', visa_type=document.visa_type))
            
        except Exception as e:
            db.session.rollback()
            error_message = f"更新文档时出错：{str(e)}"
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
            
            flash(error_message, "error")
            return redirect(url_for('visa_documents.manage_visas'))
    
    # GET 请求处理
    visa_type = request.args.get('visa_type', '')
    country_id = request.args.get('country', type=int)

    # 查询所有签证类型列表供选择框使用
    visa_types = [type.visa_type for type in VisaTypes.query.order_by(VisaTypes.visa_type).all()]
    
    # 查询所有国家列表供选择框使用
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()

    # 构建基础查询
    query = VisaDocuments.query.join(VisaTypes, VisaDocuments.visa_type == VisaTypes.visa_type)
    
    # 应用筛选条件
    if visa_type:
        query = query.filter(VisaDocuments.visa_type == visa_type)
    if country_id:
        query = query.filter(VisaTypes.country_id == country_id)
    
    documents = query.all()

    # 如果是 AJAX 请求，返回 JSON 格式的数据
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'html': render_template('visas/visa_document_table.html', documents=documents)
        })

    return render_template('visas/visa_document.html', 
                         documents=documents, 
                         visa_types=visa_types,
                         countries=countries,
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


@visa_documents.route('/get_identity_options/<visa_type>')
def get_identity_options(visa_type):
    try:
        # 添加调试日志
        print(f"正在获取签证类型 '{visa_type}' 的身份选项")
        
        # 使用 distinct 查询确保只获取实际存在的身份
        identity_options = db.session.query(VisaDocuments.singapore_identity)\
            .filter(VisaDocuments.visa_type == visa_type)\
            .filter(VisaDocuments.singapore_identity != 'SHARE')\
            .distinct()\
            .all()
        
        # 打印查询结果
        print(f"数据库查询结果: {identity_options}")
        
        # 将查询结果转换为列表
        identity_options = [option[0] for option in identity_options]
        print(f"处理后的身份选项列表: {identity_options}")
        
        # 检查数据库中的所有记录
        all_documents = VisaDocuments.query.filter_by(visa_type=visa_type).all()
        print(f"该签证类型的所有记录:")
        for doc in all_documents:
            print(f"ID: {doc.id}, 签证类型: {doc.visa_type}, 身份: {doc.singapore_identity}")
        
        return jsonify({
            'success': True,
            'identity_options': identity_options
        })
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@visa_documents.route('/get_all_identities')
def get_all_identities():
    try:
        # 从 VisaSingaporeIdentity 表获取所有身份
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        
        # 转换为列表格式
        identity_list = [identity.to_dict() for identity in identities]
        
        return jsonify({
            'success': True,
            'identities': identity_list
        })
    except Exception as e:
        print(f"获取所有身份时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@visa_documents.route('/get_visa_types')
def get_visa_types():
    try:
        # 获取国家ID参数
        country_id = request.args.get('country_id', type=int)
        
        # 构建基础查询
        query = db.session.query(
            VisaTypes.visa_type,
            VisaTypes.country_id
        )
        
        # 如果提供了国家ID，添加筛选条件
        if country_id:
            query = query.filter(VisaTypes.country_id == country_id)
        
        # 执行查询
        visa_types = query.all()
        
        # 转换为列表格式
        visa_types_list = [
            {
                'visa_type': vt.visa_type,
                'country_id': vt.country_id
            }
            for vt in visa_types
        ]
        
        return jsonify({
            'success': True,
            'visa_types': visa_types_list
        })
    except Exception as e:
        print(f"获取签证类型时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
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
