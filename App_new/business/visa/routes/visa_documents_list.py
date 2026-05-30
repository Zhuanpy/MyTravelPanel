from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from App_new.business.visa.models.Visamodels import VisaDocumentsList
from App_new.exts import db, csrf
from App_new.utils.decorators import staff_only

visa_documents_list = Blueprint('visa_documents_list', __name__)

@visa_documents_list.route('/list')
@login_required
@staff_only
def documents_list():
    """显示文档列表页面"""
    try:
        # 获取查询参数
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20  # 每页显示20条
        
        # 构建查询
        query = VisaDocumentsList.query
        
        # 应用搜索过滤（中英文名称均可匹配）
        if search:
            query = query.filter(db.or_(
                VisaDocumentsList.name.like(f'%{search}%'),
                VisaDocumentsList.name_en.like(f'%{search}%')
            ))
        
        # 应用分类过滤
        if category:
            query = query.filter(VisaDocumentsList.category == category)
        
        # 获取分页数据
        pagination = query.order_by(VisaDocumentsList.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        documents = pagination.items
        
        # 获取所有分类
        categories = db.session.query(VisaDocumentsList.category).distinct().filter(
            VisaDocumentsList.category.isnot(None),
            VisaDocumentsList.category != ''
        ).all()
        category_list = [cat[0] for cat in categories]
        
        return render_template('business/visa/签证文档管理/visa_documents_list.html', 
                             documents=documents, 
                             categories=category_list,
                             pagination=pagination)
        
    except Exception as e:
        flash(f'获取文档列表失败: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))

@visa_documents_list.route('/add', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def add_document():
    """添加新文档"""
    try:
        # 获取表单数据
        name = request.form.get('name')
        name_en = request.form.get('name_en', '')
        description = request.form.get('description', '')
        category = request.form.get('category', '')

        # 验证必填字段
        if not name:
            return jsonify({
                'success': False,
                'message': '文档名称不能为空'
            }), 400

        # 检查名称是否已存在
        existing_doc = VisaDocumentsList.query.filter_by(name=name).first()
        if existing_doc:
            return jsonify({
                'success': False,
                'message': '文档名称已存在'
            }), 400

        # 创建新文档
        new_document = VisaDocumentsList(
            name=name,
            name_en=name_en,
            description=description,
            category=category
        )
        
        db.session.add(new_document)
        db.session.commit()
        
        # 转换为字典格式
        document_dict = new_document.to_dict()
        
        return jsonify({
            'success': True,
            'message': '文档添加成功',
            'document': document_dict
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"添加文档时发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': f'添加文档失败: {str(e)}'
        }), 500

@visa_documents_list.route('/<int:document_id>', methods=['GET'])
def get_document(document_id):
    """获取单个文档信息"""
    try:
        document = VisaDocumentsList.query.get_or_404(document_id)
        
        # 转换为字典格式
        document_dict = document.to_dict()
        
        return jsonify({
            'success': True,
            'document': document_dict
        })
        
    except Exception as e:
        import traceback
        print(f"获取文档信息时发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': f'获取文档信息失败: {str(e)}'
        }), 500

@visa_documents_list.route('/<int:document_id>', methods=['PUT'])
def update_document(document_id):
    """更新文档信息"""
    try:
        document = VisaDocumentsList.query.get_or_404(document_id)
        
        # 获取表单数据
        name = request.form.get('name')
        name_en = request.form.get('name_en', '')
        description = request.form.get('description', '')
        category = request.form.get('category', '')

        # 验证必填字段
        if not name:
            return jsonify({
                'success': False,
                'message': '文档名称不能为空'
            }), 400

        # 检查名称是否已存在（排除当前文档）
        existing_doc = VisaDocumentsList.query.filter(
            VisaDocumentsList.name == name,
            VisaDocumentsList.id != document_id
        ).first()
        if existing_doc:
            return jsonify({
                'success': False,
                'message': '文档名称已存在'
            }), 400

        # 更新文档信息
        document.name = name
        document.name_en = name_en
        document.description = description
        document.category = category
        
        db.session.commit()
        
        # 转换为字典格式
        document_dict = document.to_dict()
        
        return jsonify({
            'success': True,
            'message': '文档更新成功',
            'document': document_dict
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"更新文档时发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': f'更新文档失败: {str(e)}'
        }), 500

@visa_documents_list.route('/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """删除文档"""
    try:
        document = VisaDocumentsList.query.get_or_404(document_id)
        
        # 检查是否有关联的签证类型
        if hasattr(document, 'visa_types') and document.visa_types:
            return jsonify({
                'success': False,
                'message': '无法删除：该文档已被签证类型使用'
            }), 400
        
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '文档删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除文档失败: {str(e)}'
        }), 500

@visa_documents_list.route('/categories')
def get_categories():
    """获取所有文档分类"""
    try:
        categories = db.session.query(VisaDocumentsList.category).distinct().filter(
            VisaDocumentsList.category.isnot(None),
            VisaDocumentsList.category != ''
        ).all()
        
        category_list = [cat[0] for cat in categories]
        
        return jsonify({
            'success': True,
            'categories': category_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取分类失败: {str(e)}'
        }), 500

@visa_documents_list.route('/bulk_operations', methods=['POST'])
@csrf.exempt
def bulk_operations():
    """批量操作文档"""
    try:
        operation = request.form.get('operation')
        document_ids = request.form.getlist('document_ids[]')
        
        if not document_ids:
            return jsonify({
                'success': False,
                'message': '请选择要操作的文档'
            }), 400
        
        documents = VisaDocumentsList.query.filter(VisaDocumentsList.id.in_(document_ids)).all()
        
        if operation == 'delete':
            # 批量删除
            for doc in documents:
                if hasattr(doc, 'visa_types') and doc.visa_types:
                    return jsonify({
                        'success': False,
                        'message': f'无法删除文档"{doc.name}"：该文档已被签证类型使用'
                    }), 400
                db.session.delete(doc)
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'成功删除 {len(documents)} 个文档'
            })
        
        elif operation == 'update_category':
            # 批量更新分类
            new_category = request.form.get('new_category', '')
            for doc in documents:
                doc.category = new_category
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'成功更新 {len(documents)} 个文档的分类'
            })
        
        else:
            return jsonify({
                'success': False,
                'message': '不支持的操作类型'
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'批量操作失败: {str(e)}'
        }), 500

@visa_documents_list.route('/export')
def export_documents():
    """导出文档列表"""
    try:
        # 获取所有文档
        documents = VisaDocumentsList.query.order_by(VisaDocumentsList.id).all()
        
        # 准备导出数据
        export_data = []
        for doc in documents:
            export_data.append({
                'ID': doc.id,
                '文档名称': doc.name,
                '英文名称': doc.name_en or '',
                '描述': doc.description or '',
                '分类': doc.category or ''
            })
        
        return jsonify({
            'success': True,
            'data': export_data,
            'filename': f'签证文档列表_{len(export_data)}条记录'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'导出失败: {str(e)}'
        }), 500

@visa_documents_list.route('/import', methods=['POST'])
@csrf.exempt
def import_documents():
    """导入文档列表"""
    try:
        # 这里可以添加文件上传和解析逻辑
        # 暂时返回占位符
        return jsonify({
            'success': False,
            'message': '导入功能正在开发中'
        }), 501
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500
