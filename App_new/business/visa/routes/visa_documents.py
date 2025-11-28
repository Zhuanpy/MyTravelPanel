from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from App_new.exts import db, csrf
from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaCountries, VisaDocumentsList
from App_new.utils.decorators import staff_only
import logging
from urllib.parse import unquote
import html

"""
签证文档管理 (visa_documents.py):
管理签证资料 (/visa/documents/manage_visas)
添加文档 (/visa/documents/add_document)
编辑文档 (/visa/documents/edit/<id>)
删除文档 (/visa/documents/delete/<id>)

"""
visa_documents = Blueprint('visa_documents', __name__)

@visa_documents.route('/manage_visas', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def manage_visas():
    if request.method == 'POST':
        try:
            # 添加调试日志
            logging.info(f"收到编辑请求，表单数据: {dict(request.form)}")
            
            document_id = request.form.get('document_id')
            document = VisaDocuments.query.get_or_404(document_id)
            
            # 记录原始值
            original_identity_id = document.singapore_identity_id
            logging.info(f"原始新加坡身份ID: {original_identity_id}")
            
            # 获取新的身份值
            new_identity_id = request.form.get('singapore_identity')
            logging.info(f"接收到的新加坡身份ID: {new_identity_id}")
            
            # 更新文档信息
            document.visa_type_id = request.form.get('visa_type')
            document.singapore_identity_id = new_identity_id if new_identity_id else None
            document.additional_info = request.form.get('additional_info', '')
            
            # 记录更新后的值
            logging.info(f"更新后的新加坡身份ID: {document.singapore_identity_id}")
            
            # 处理选择的文档ID（如果有的话）
            selected_document_id = request.form.get('selected_document_id')
            if selected_document_id:
                try:
                    selected_doc = VisaDocumentsList.query.get(int(selected_document_id))
                    if selected_doc:
                        # 可以选择将选择的文档信息存储到某个字段中
                        # 这里我们暂时只记录日志
                        logging.info(f"用户选择了文档: {selected_doc.name} (ID: {selected_doc.id})")
                except (ValueError, TypeError):
                    pass  # 忽略无效的文档ID
            
            # 处理多选文档ID
            selected_document_ids = request.form.getlist('selected_document_ids[]')
            if selected_document_ids:
                try:
                    # 清除现有的关联
                    document.selected_documents.clear()
                    
                    # 添加新选择的文档
                    for doc_id in selected_document_ids:
                        doc = VisaDocumentsList.query.get(int(doc_id))
                        if doc:
                            document.selected_documents.append(doc)
                            logging.info(f"添加文档关联: {doc.name} (ID: {doc.id})")
                except (ValueError, TypeError) as e:
                    logging.error(f"处理多选文档时出错: {str(e)}")
            
            db.session.commit()
            logging.info(f"数据库提交成功，最终新加坡身份ID: {document.singapore_identity_id}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': '文档更新成功'
                })
            
            flash("文档更新成功", "success")
            return redirect(url_for('visa_documents.manage_visas', visa_type=document.visa_type.visa_type))
            
        except Exception as e:
            db.session.rollback()
            error_message = f"更新文档时出错：{str(e)}"
            logging.error(f"更新文档时出错: {str(e)}")
            
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
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示10条记录

    # 查询所有签证类型列表供选择框使用
    visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
    
    # 查询所有国家列表供选择框使用
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    
    # 查询所有新加坡身份列表供选择框使用
    singapore_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()

    # 构建基础查询
    query = VisaDocuments.query.join(VisaTypes, VisaDocuments.visa_type_id == VisaTypes.id)
    
    # 应用筛选条件
    if visa_type:
        query = query.filter(VisaTypes.visa_type == visa_type)
    if country_id:
        query = query.filter(VisaTypes.country_id == country_id)
    
    # 获取分页数据
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items

    # 如果是 AJAX 请求，返回 JSON 格式的数据
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'html': render_template('business/visa/签证文档管理/visa_document_table.html', documents=documents)
        })

    return render_template('business/visa/签证文档管理/visa_document.html',
                         documents=documents, 
                         visa_types=visa_types,
                         countries=countries,
                         singapore_identities=singapore_identities,
                         current_visa_type=visa_type,
                         pagination=pagination)

@visa_documents.route('/add_document', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def add_document():
    if request.method == 'GET':
        visa_type = request.args.get('visa_type', '')
        # 重定向到管理页面，因为add_document.html模板可能不存在
        return redirect(url_for('visa_documents.manage_visas', visa_type=visa_type))
        
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type_id = request.form.get('visa_type')
            singapore_identity_id = request.form.get('singapore_identity')
            document_info = request.form.get('document_info', '')
            additional_info = request.form.get('additional_info', '')

            # 数据验证
            if not all([visa_type_id, singapore_identity_id]):
                flash("签证类型和新加坡身份为必填字段", "error")
                return redirect(url_for('visa_documents.add_document', visa_type=visa_type_id))

            # 检查是否已存在相同签证类型和身份的记录
            existing = VisaDocuments.query.filter_by(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id
            ).first()
            
            if existing:
                flash(f"已存在相同签证类型和身份的记录", "error")
                return redirect(url_for('visa_documents.add_document', visa_type=visa_type_id))

            # 创建新记录
            new_document = VisaDocuments(
                visa_type_id=visa_type_id,
                singapore_identity_id=singapore_identity_id,
                document_info=document_info,
                additional_info=additional_info
            )

            db.session.add(new_document)
            db.session.commit()
            flash("签证文档已添加", "success")
            
            # 获取签证类型名称用于重定向
            visa_type = VisaTypes.query.get(visa_type_id)
            return redirect(url_for('visa_documents.manage_visas', visa_type=visa_type.visa_type if visa_type else ''))
            
        except Exception as e:
            db.session.rollback()
            flash(f"添加文档时出错：{str(e)}", "error")
            return redirect(url_for('visa_documents.add_document', visa_type=visa_type_id))

@visa_documents.route('/edit/<int:id>', methods=['GET'])
@login_required
@staff_only
def edit_document(id):
    document = VisaDocuments.query.get_or_404(id)
    return render_template('business/visa/签证文档管理/visa_document_edit.html', document=document)

@visa_documents.route('/update/<int:id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def update_document(id):
    document = VisaDocuments.query.get_or_404(id)
    
    try:
        document.additional_info = request.form.get('additional_info', '')
        
        db.session.commit()
        flash("文档更新成功", "success")
        return redirect(url_for('visa_documents.manage_visas', visa_type=document.visa_type.visa_type))
        
    except Exception as e:
        db.session.rollback()
        flash(f"更新文档时出错：{str(e)}", "error")
        return redirect(url_for('visa_documents.edit_document', id=id))

@visa_documents.route('/delete/<int:id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_document(id):
    document = VisaDocuments.query.get_or_404(id)
    visa_type = document.visa_type.visa_type
    
    try:
        db.session.delete(document)
        db.session.commit()
        flash("文档删除成功", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"删除文档时出错：{str(e)}", "error")
    
    return redirect(url_for('visa_documents.manage_visas', visa_type=visa_type))

@visa_documents.route('/delete_visa_document', methods=['POST'])
@csrf.exempt
def delete_visa_document():
    """删除签证文档的API接口"""
    try:
        # 获取JSON数据
        data = request.get_json()
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({
                'success': False,
                'message': '缺少文档ID'
            }), 400
        
        # 查找文档
        document = VisaDocuments.query.get(document_id)
        if not document:
            return jsonify({
                'success': False,
                'message': '文档不存在'
            }), 404
        
        # 删除文档
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '文档删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除签证文档时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除文档时出错：{str(e)}'
        }), 500

@visa_documents.route('/document_request/<visa_type>/<singapore_status>')
def display_document_request(visa_type, singapore_status):
    """
    从数据库中获取签证文件资料内容，并返回 JSON 格式的响应。

    参数:
    - visa_type (str): 签证类型名称
    - singapore_status (str): 新加坡身份状态

    返回:
    - dict: 包含签证文件资料内容的 JSON 响应
    """
    try:
        # URL解码参数
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        decoded_singapore_status = unquote(singapore_status)
        decoded_singapore_status = html.unescape(decoded_singapore_status)
        
        print(f"DEBUG: 原始参数 - visa_type: '{visa_type}', singapore_status: '{singapore_status}'")
        print(f"DEBUG: 解码后 - visa_type: '{decoded_visa_type}', singapore_status: '{decoded_singapore_status}'")
        
        # 根据签证类型名称获取ID
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'document_info': '签证类型不存在',
                'additional_info': '签证类型不存在'
            }), 404
        
        # 根据身份名称获取ID
        identity_record = None
        if decoded_singapore_status != 'SHARE':
            # 去除可能的前后空格
            clean_status = decoded_singapore_status.strip()
            print(f"DEBUG: 查询身份 - clean_status: '{clean_status}'")
            
            # 查询所有身份记录用于调试
            all_identities = VisaSingaporeIdentity.query.all()
            print(f"DEBUG: 数据库中所有身份: {[(i.id, i.identity_zh) for i in all_identities]}")
            
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=clean_status).first()
            if not identity_record:
                print(f"DEBUG: 未找到身份记录 - clean_status: '{clean_status}'")
                return jsonify({
                    'document_info': f'身份类型不存在: {clean_status}',
                    'additional_info': f'身份类型不存在: {clean_status}'
                }), 404
        
        print(f"DEBUG: visa_type_record.id: {visa_type_record.id}, identity_record.id: {identity_record.id if identity_record else None}")
        
        # 查询该签证类型下的所有文档记录用于调试
        all_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        print(f"DEBUG: 该签证类型下的所有文档记录: {[(d.id, d.singapore_identity_id) for d in all_docs]}")
        
        # 获取文档信息
        document_info = VisaDocuments.get_document_info(
            visa_type_record.id, 
            identity_record.id if identity_record else None  # SHARE使用None
        )

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
        # URL解码签证类型
        decoded_visa_type = unquote(visa_type)
        # 处理可能的HTML实体编码
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        print(f"原始签证类型: '{visa_type}'")
        print(f"URL解码后: '{decoded_visa_type}'")
        
        # 验证签证类型是否存在
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            print(f"签证类型 '{decoded_visa_type}' 不存在")
            return jsonify({
                'success': False,
                'message': f'签证类型 {decoded_visa_type} 不存在',
                'identity_options': []
            }), 404
        
        # 从 VisaDocuments 表获取该签证类型实际已选择的身份（排除SHARE）
        selected_identities = db.session.query(VisaSingaporeIdentity.identity_zh)\
            .join(VisaDocuments, VisaDocuments.singapore_identity_id == VisaSingaporeIdentity.id)\
            .filter(VisaDocuments.visa_type_id == visa_type_record.id)\
            .filter(VisaDocuments.singapore_identity_id.isnot(None))\
            .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
            .distinct()\
            .all()
        
        # 将查询结果转换为列表
        identity_options = [identity[0] for identity in selected_identities]
        
        print(f"从VisaDocuments表获取的当前已选择身份（排除SHARE）: {identity_options}")
        
        return jsonify({
            'success': True,
            'identity_options': identity_options
        })
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'identity_options': []
        }), 500


@visa_documents.route('/get_all_identities')
def get_all_identities():
    try:
        # 从 VisaSingaporeIdentity 表获取所有身份，排除SHARE
        identities = VisaSingaporeIdentity.query\
            .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
            .order_by(VisaSingaporeIdentity.identity_zh)\
            .all()
        
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


@visa_documents.route('/api/visa/identity-documents')
def get_identity_documents():
    try:
        visa_type = request.args.get('visa_type')
        identity_id = request.args.get('identity_id')
        
        if not visa_type or not identity_id:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400

        # 从VisaDocuments表获取该身份需要的文档信息
        document = VisaDocuments.query.filter_by(
            visa_type=visa_type,
            singapore_identity=identity_id
        ).first()

        if not document:
            return jsonify({
                'success': False,
                'message': '未找到相关文档'
            }), 404

        # 使用get_document_info方法获取文档信息
        document_info_result = VisaDocuments.get_document_info(
            document.visa_type_id,
            document.singapore_identity_id
        )
        
        document_info = document_info_result.get('document_info', '')
        additional_info = document_info_result.get('additional_info', '')

        # 将文档信息转换为前端需要的格式
        documents = []
        
        # 处理共用资料
        if '【共用资料】' in document_info:
            common_docs = document_info.split('【共用资料】')[1].split('【特定身份资料】')[0].strip()
            for doc in common_docs.split('\n'):
                if doc.strip():
                    documents.append({
                        'name': doc.strip(),
                        'url': '#',
                        'icon': 'fa-file-alt'
                    })

        # 处理特定身份资料
        if '【特定身份资料】' in document_info:
            specific_docs = document_info.split('【特定身份资料】')[1].strip()
            for doc in specific_docs.split('\n'):
                if doc.strip():
                    documents.append({
                        'name': doc.strip(),
                        'url': '#',
                        'icon': 'fa-file-alt'
                    })

        return jsonify({
            'success': True,
            'documents': documents,
            'additional_info': additional_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@visa_documents.route('/get_documents_list')
def get_documents_list():
    """获取文档列表供选择"""
    try:
        # 获取查询参数
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        page = request.args.get('page', 1, type=int)
        per_page = 5  # 每页显示5个文档
        
        # 构建查询
        query = VisaDocumentsList.query
        
        # 应用搜索过滤
        if search:
            query = query.filter(VisaDocumentsList.name.like(f'%{search}%'))
        
        # 应用分类过滤
        if category:
            query = query.filter(VisaDocumentsList.category == category)
        
        # 获取分页数据
        pagination = query.order_by(VisaDocumentsList.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 转换为字典格式
        documents_list = [doc.to_dict() for doc in pagination.items]
        
        # 获取所有可用的分类（从visa_documents_list表的category字段）
        all_categories = db.session.query(VisaDocumentsList.category)\
            .filter(VisaDocumentsList.category.isnot(None))\
            .filter(VisaDocumentsList.category != '')\
            .distinct()\
            .order_by(VisaDocumentsList.category)\
            .all()
        
        categories_list = [cat[0] for cat in all_categories]
        
        # 获取按分类组织的所有文档（用于分类显示）
        all_documents_by_category = {}
        for cat in categories_list:
            category_docs = VisaDocumentsList.query\
                .filter(VisaDocumentsList.category == cat)\
                .order_by(VisaDocumentsList.name)\
                .all()
            all_documents_by_category[cat] = [doc.to_dict() for doc in category_docs]
        
        return jsonify({
            'success': True,
            'documents': documents_list,
            'categories': categories_list,  # 添加分类列表
            'documents_by_category': all_documents_by_category,  # 按分类组织的文档（全部显示）
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文档列表失败: {str(e)}'
        }), 500

@visa_documents.route('/get_document_content/<int:document_id>')
def get_document_content(document_id):
    """获取指定文档的内容"""
    try:
        document = VisaDocumentsList.query.get_or_404(document_id)
        
        return jsonify({
            'success': True,
            'document': {
                'id': document.id,
                'name': document.name,
                'description': document.description,
                'category': document.category
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文档内容失败: {str(e)}'
        }), 500

@visa_documents.route('/test_documents_data/<visa_type>')
def test_documents_data(visa_type):
    """测试签证文档数据"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        print(f"DEBUG: 签证类型ID: {visa_type_record.id}")
        
        # 查询所有相关的文档记录
        docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        print(f"DEBUG: 找到 {len(docs)} 个文档记录")
        
        result = {
            'visa_type': visa_type_record.visa_type,
            'visa_type_id': visa_type_record.id,
            'total_docs': len(docs),
            'documents': []
        }
        
        for doc in docs:
            doc_info = {
                'id': doc.id,
                'visa_type_id': doc.visa_type_id,
                'singapore_identity_id': doc.singapore_identity_id,
                'identity_name': doc.singapore_identity.identity_zh if doc.singapore_identity else 'SHARE共用资料',
                'selected_documents_count': len(doc.selected_documents) if doc.selected_documents else 0,
                'selected_documents': [d.name for d in doc.selected_documents] if doc.selected_documents else [],
                'additional_info': doc.additional_info
            }
            result['documents'].append(doc_info)
            print(f"DEBUG: 文档记录 - ID: {doc.id}, 身份: {doc_info['identity_name']}, 文档数量: {doc_info['selected_documents_count']}")
            
            # 特别关注SHARE记录
            if doc.singapore_identity_id is None:
                print(f"DEBUG: SHARE记录详情 - ID: {doc.id}")
                print(f"DEBUG: SHARE记录 - selected_documents: {doc.selected_documents}")
                print(f"DEBUG: SHARE记录 - additional_info: {doc.additional_info}")
                if doc.selected_documents:
                    print(f"DEBUG: SHARE记录 - 文档列表: {[d.name for d in doc.selected_documents]}")
                else:
                    print(f"DEBUG: SHARE记录 - 没有关联的文档")
        
        return jsonify(result)
    except Exception as e:
        print(f"DEBUG: 测试数据时出错: {str(e)}")
        return jsonify({'error': str(e)})

@visa_documents.route('/check_share_documents/<visa_type>')
def check_share_documents(visa_type):
    """检查SHARE共用资料记录"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 检查是否存在SHARE记录
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        result = {
            'visa_type': visa_type_record.visa_type,
            'visa_type_id': visa_type_record.id,
            'share_document_exists': share_doc is not None,
            'share_document_id': share_doc.id if share_doc else None,
            'share_documents_count': len(share_doc.selected_documents) if share_doc and share_doc.selected_documents else 0,
            'share_documents': [d.name for d in share_doc.selected_documents] if share_doc and share_doc.selected_documents else [],
            'additional_info': share_doc.additional_info if share_doc else None
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@visa_documents.route('/create_share_documents/<visa_type>', methods=['POST'])
@csrf.exempt
def create_share_documents(visa_type):
    """创建SHARE共用资料记录"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 检查是否已存在SHARE记录
        existing_share = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        if existing_share:
            return jsonify({'message': 'SHARE记录已存在', 'id': existing_share.id})
        
        # 创建新的SHARE记录
        new_share_doc = VisaDocuments(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None,  # SHARE记录
            additional_info='待输入'
        )
        
        db.session.add(new_share_doc)
        db.session.commit()
        
        return jsonify({
            'message': 'SHARE记录创建成功',
            'id': new_share_doc.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

@visa_documents.route('/add_common_documents/<visa_type>', methods=['POST'])
@csrf.exempt
def add_common_documents(visa_type):
    """为SHARE记录添加常用共用文档"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 获取SHARE记录
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        if not share_doc:
            return jsonify({'error': 'SHARE记录不存在'})
        
        # 常用共用文档名称
        common_documents = [
            '护照原件',
            '护照复印件',
            '近期护照照片',
            '身份证复印件',
            '出生证明',
            '结婚证明（如适用）',
            '学历证明',
            '工作证明',
            '银行对账单',
            '申请表'
        ]
        
        # 查找或创建这些文档
        added_docs = []
        for doc_name in common_documents:
            # 查找是否已存在该文档
            existing_doc = VisaDocumentsList.query.filter_by(name=doc_name).first()
            if not existing_doc:
                # 创建新文档
                new_doc = VisaDocumentsList(
                    name=doc_name,
                    category='共用资料'
                )
                db.session.add(new_doc)
                db.session.flush()  # 获取ID
                existing_doc = new_doc
            
            # 添加到SHARE记录
            if existing_doc not in share_doc.selected_documents:
                share_doc.selected_documents.append(existing_doc)
                added_docs.append(doc_name)
        
        db.session.commit()
        
        return jsonify({
            'message': f'成功添加 {len(added_docs)} 个共用文档',
            'added_documents': added_docs,
            'total_documents': len(share_doc.selected_documents)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

@visa_documents.route('/debug_share_documents/<visa_type>')
def debug_share_documents(visa_type):
    """详细调试SHARE文档的多对多关系"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 获取SHARE记录
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        if not share_doc:
            return jsonify({'error': 'SHARE记录不存在'})
        
        # 直接查询关联表
        from sqlalchemy import text
        query = text("""
            SELECT vdl.id, vdl.name, vdl.category
            FROM visa_documents_list vdl
            JOIN visa_document_documents vdd ON vdl.id = vdd.document_id
            WHERE vdd.visa_document_id = :doc_id
        """)
        
        result = db.session.execute(query, {'doc_id': share_doc.id})
        associated_docs = [{'id': row[0], 'name': row[1], 'category': row[2]} for row in result]
        
        # 检查所有可用的文档
        all_docs = VisaDocumentsList.query.all()
        all_docs_list = [{'id': doc.id, 'name': doc.name, 'category': doc.category} for doc in all_docs]
        
        debug_info = {
            'visa_type': visa_type_record.visa_type,
            'visa_type_id': visa_type_record.id,
            'share_document_id': share_doc.id,
            'share_document_visa_type_id': share_doc.visa_type_id,
            'share_document_identity_id': share_doc.singapore_identity_id,
            'share_document_additional_info': share_doc.additional_info,
            'associated_documents_count': len(associated_docs),
            'associated_documents': associated_docs,
            'all_documents_count': len(all_docs_list),
            'all_documents': all_docs_list[:10],  # 只显示前10个
            'relationship_check': {
                'selected_documents_type': str(type(share_doc.selected_documents)),
                'selected_documents_length': len(share_doc.selected_documents) if share_doc.selected_documents else 0,
                'selected_documents_list': [d.name for d in share_doc.selected_documents] if share_doc.selected_documents else []
            }
        }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': str(e.__traceback__)})

#


@visa_documents.route('/fix_share_documents/<visa_type>', methods=['POST'])
@csrf.exempt
def fix_share_documents_route(visa_type):
    """修复指定签证类型的SHARE文档问题"""
    try:
        from App_new.utils.visa_debug import fix_share_documents

        # 执行修复
        success = fix_share_documents(visa_type)

        if success:
            return jsonify({
                'success': True,
                'message': f'签证类型 {visa_type} 的SHARE文档已修复'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'修复失败：签证类型 {visa_type} 不存在'
            })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'修复过程中出错: {str(e)}'
        })


@visa_documents.route('/debug_visa_documents/<visa_type>')
def debug_visa_documents_route(visa_type):
    """调试指定签证类型的文档数据"""
    try:
        from App_new.utils.visa_debug import debug_visa_documents

        # 执行调试
        success = debug_visa_documents(visa_type)

        return jsonify({
            'success': success,
            'message': f'调试完成，请查看控制台输出'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'调试过程中出错: {str(e)}'
        })


@visa_documents.route('/check_all_share_records')
def check_all_share_records():
    """检查所有签证类型的SHARE记录状态"""
    try:
        from App_new.utils.visa_debug import check_all_visa_types

        missing_types = check_all_visa_types()

        return jsonify({
            'success': True,
            'missing_share_records': missing_types,
            'total_missing': len(missing_types),
            'message': f'检查完成，{len(missing_types)} 个签证类型缺少SHARE记录'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查过程中出错: {str(e)}'
        })
