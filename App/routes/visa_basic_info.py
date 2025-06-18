from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from ..exts import db
from ..models import VisaCountries, VisaTypes, VisaSingaporeIdentity, VisaDocuments
from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField
from wtforms.validators import DataRequired
import time

"""
管理 (visa_basic_info.py):
管理身份信息 (/visa/basic/manage_identities)
管理国家信息 (/visa/basic/manage_countries)

"""

visa_basic = Blueprint('visa_basic', __name__)

def create_response(message, status=200):
    """生成标准化的 JSON 响应"""
    return jsonify(message=message), status


def add_to_db(instance):
    """尝试将记录添加到数据库并提交事务"""
    try:
        db.session.add(instance)
        db.session.commit()
        return create_response("添加成功", 201)
    except Exception as e:
        db.session.rollback()  # 遇到异常回滚
        return create_response(f"添加失败: {str(e)}", 400)

""" visa singapore  identity start """
@visa_basic.route('/manage_identities', methods=['GET', 'POST'])
def manage_identities():
    """管理新加坡身份信息"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            identity_zh = request.form.get('identity_zh')
            identity_en = request.form.get('identity_en')
            remarks = request.form.get('remarks')

            # 创建新的身份记录
            new_identity = VisaSingaporeIdentity(
                identity_zh=identity_zh,
                identity_en=identity_en,
                remarks=remarks
            )

            # 保存到数据库
            db.session.add(new_identity)
            db.session.commit()

            flash('身份信息添加成功！', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败：{str(e)}', 'error')

    # 获取所有身份信息
    identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
    return render_template('visas/manage_identities.html', identities=identities)

@visa_basic.route('/delete_identity/<int:identity_id>', methods=['POST'])
def delete_identity(identity_id):
    identity = VisaSingaporeIdentity.query.get_or_404(identity_id)
    db.session.delete(identity)
    db.session.commit()
    flash('身份信息删除成功！', 'success')
    return redirect(url_for('visa_basic.manage_identities'))

""" visa singapore  identity end """



""" visa  country start """

@visa_basic.route('/manage_countries', methods=['GET', 'POST'])
def manage_countries():
    if request.method == 'POST':
        try:
            country_name_CN = request.form.get('country_name_CN')
            country_name_EN = request.form.get('country_name_EN')
            country_code = request.form.get('country_code')

            # 检查是否已存在相同国家
            existing_country = VisaCountries.query.filter_by(country_name_CN=country_name_CN).first()
            if existing_country:
                flash('该国家已存在！', 'error')
                return redirect(url_for('visa_basic.manage_countries'))

            # 创建新国家
            new_country = VisaCountries(
                country_name_CN=country_name_CN,
                country_name_EN=country_name_EN,
                country_code=country_code
            )

            db.session.add(new_country)
            db.session.commit()
            flash('国家添加成功！', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'添加失败: {str(e)}', 'error')

    # 获取所有国家列表，并通过关联的签证类型进行排序
    countries = db.session.query(VisaCountries) \
        .join(VisaTypes, VisaCountries.id == VisaTypes.country_id, isouter=True) \
        .group_by(VisaCountries.id) \
        .order_by(db.func.min(VisaTypes.visa_type)) \
        .all()

    return render_template('visas/manage_countries.html', countries=countries)

@visa_basic.route('/add_country', methods=['POST'])
def add_country():
    data = request.get_json()
    country = VisaCountries(
        country_name_CN=data['country_name_CN'],
        country_name_EN=data['country_name_EN'],
        country_code=data['country_code']
    )
    return add_to_db(country)

""" visa  country end """



""" about visa type start """

# visa_type_list
@visa_basic.route('/visa/visa_type_list', methods=['GET'])
def visa_type_list():
    # 获取筛选参数
    country_id = request.args.get('country', type=int)
    # 获取页码参数，默认为1
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示20条数据
    
    # 获取所有国家列表（用于筛选下拉框）
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    
    # 获取所有新加坡身份列表（用于添加签证类型）
    singapore_identities = VisaSingaporeIdentity.query\
        .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
        .order_by(VisaSingaporeIdentity.identity_zh)\
        .all()
    
    # 构建基础查询
    query = VisaTypes.query
    
    # 应用国家筛选
    if country_id:
        query = query.filter_by(country_id=country_id)
    
    # 获取分页数据
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    visa_types = pagination.items
    
    # 为每个签证类型获取实际的身份选项
    for vt in visa_types:
        # 从 VisaDocuments 中获取该签证类型的实际身份选项
        actual_identities = db.session.query(VisaSingaporeIdentity.identity_zh)\
            .join(VisaDocuments, VisaDocuments.singapore_identity_id == VisaSingaporeIdentity.id)\
            .filter(VisaDocuments.visa_type_id == vt.id)\
            .filter(VisaDocuments.singapore_identity_id.isnot(None))\
            .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
            .distinct()\
            .all()
        
        # 将查询结果转换为列表
        vt.actual_identities = [identity[0] for identity in actual_identities]
    
    return render_template('visas/visa_type_list.html', 
                         visa_types=visa_types,
                         countries=countries,
                         singapore_identities=singapore_identities,
                         pagination=pagination)

@visa_basic.route('/add_visa_type', methods=['GET', 'POST'])
def add_visa_type():
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type = request.form.get('visa_type')
            processing_time = request.form.get('processing_time')
            fee = request.form.get('fee')
            country_id = request.form.get('country_id')
            identity_ids = request.form.getlist('identity_ids')  # 获取多个身份ID

            # 创建新的签证类型
            new_visa_type = VisaTypes(
                visa_type=visa_type,
                processing_time=processing_time,
                fee=fee,
                country_id=country_id
            )

            # 添加身份关联
            if identity_ids:
                identities = VisaSingaporeIdentity.query.filter(VisaSingaporeIdentity.id.in_(identity_ids)).all()
                for identity in identities:
                    new_doc = VisaDocuments(
                        visa_type_id=new_visa_type.id,
                        singapore_identity_id=identity.id,
                        document_info='待输入',
                        additional_info='待输入'
                    )
                    db.session.add(new_doc)

            # 创建签证类型对应的文件夹结构
            project_root = Path(__file__).resolve().parent.parent

            # 创建签证资源文件夹
            visa_resource_folder = project_root / "static" / "资源" / "签证" / visa_type
            visa_resource_folder.mkdir(parents=True, exist_ok=True)

            # 创建共用资料文件夹
            shared_folder = visa_resource_folder / "共用资料"
            shared_folder.mkdir(exist_ok=True)

            # 创建身份文件夹（PR、EP、SP等）
            identity_template_folder = project_root / "static" / "资源" / "签证" / "Z-模板"
            if identity_template_folder.exists():
                for identity_folder in identity_template_folder.iterdir():
                    if identity_folder.is_dir() and identity_folder.name != "共用资料":
                        new_identity_folder = visa_resource_folder / identity_folder.name
                        new_identity_folder.mkdir(exist_ok=True)

            # 保存到数据库
            db.session.add(new_visa_type)
            db.session.commit()

            flash('签证类型添加成功！', 'success')
            return redirect(url_for('visa_basic.visa_type_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'添加失败: {str(e)}', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))

    # GET 请求处理 - 返回所有需要的数据
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    singapore_identities = VisaSingaporeIdentity.query\
        .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
        .order_by(VisaSingaporeIdentity.identity_zh)\
        .all()
    
    return jsonify({
        'countries': [{'id': c.id, 'name': c.country_name_CN} for c in countries],
        'identities': [{'id': i.id, 'name': i.identity_zh} for i in singapore_identities]
    })

class EditVisaTypeForm(FlaskForm):
    value = StringField('值', validators=[DataRequired()])

@visa_basic.route('/visa/edit_visa_type/<visa_type>/<field>', methods=['GET', 'POST'])
def edit_visa_type(visa_type, field):
    """编辑签证类型信息"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first_or_404()

        if request.method == 'POST':
            try:
                print(f"DEBUG: 开始处理POST请求，field={field}")  # 调试信息
                
                if field == 'identities':
                    # 处理身份选项更新
                    selected_identities = request.form.getlist('identities')
                    print(f"DEBUG: 选择的身份: {selected_identities}")  # 调试信息
                    print(f"DEBUG: 签证类型记录ID: {visa_type_record.id}")  # 调试信息
                    
                    # 删除现有的身份文档 - 使用更安全的方式
                    try:
                        # 先查询要删除的文档
                        docs_to_delete = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
                        print(f"DEBUG: 找到 {len(docs_to_delete)} 个要删除的文档")  # 调试信息
                        
                        for doc in docs_to_delete:
                            db.session.delete(doc)
                            print(f"DEBUG: 删除文档 ID: {doc.id}")  # 调试信息
                        
                        # 或者使用批量删除
                        # deleted_count = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).delete()
                        # print(f"DEBUG: 删除了 {deleted_count} 个现有文档")  # 调试信息
                    except Exception as e:
                        print(f"DEBUG: 删除现有文档时出错: {str(e)}")  # 调试信息
                        raise e
                    
                    # 添加新的身份文档
                    for identity_name in selected_identities:
                        try:
                            if identity_name == 'SHARE':
                                # 对于SHARE身份，创建singapore_identity_id为None的记录
                                new_doc = VisaDocuments(
                                    visa_type_id=visa_type_record.id,
                                    singapore_identity_id=None
                                )
                                db.session.add(new_doc)
                                print(f"DEBUG: 添加SHARE共用资料文档")  # 调试信息
                            else:
                                # 对于其他身份，查找对应的身份记录
                                identity = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
                                if identity:
                                    new_doc = VisaDocuments(
                                        visa_type_id=visa_type_record.id,
                                        singapore_identity_id=identity.id
                                    )
                                    db.session.add(new_doc)
                                    print(f"DEBUG: 添加文档关联: {identity_name} (ID: {identity.id})")  # 调试信息
                                else:
                                    print(f"DEBUG: 未找到身份: {identity_name}")  # 调试信息
                        except Exception as e:
                            print(f"DEBUG: 处理身份 {identity_name} 时出错: {str(e)}")  # 调试信息
                            raise e
                else:
                    # 更新费用或处理时间
                    value = request.form.get('value')
                    if field == 'fee':
                        visa_type_record.fee = value
                    else:  # processing_time
                        visa_type_record.processing_time = value

                print(f"DEBUG: 准备提交数据库更改")  # 调试信息
                db.session.commit()
                print(f"DEBUG: 数据库提交成功")  # 调试信息
                
                # 验证保存结果
                try:
                    # 重新查询验证数据是否正确保存
                    saved_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
                    print(f"DEBUG: 保存后验证 - 找到 {len(saved_docs)} 个文档")
                    for doc in saved_docs:
                        identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                        print(f"DEBUG: 保存的文档 - 身份: {identity.identity_zh if identity else 'Unknown'} (ID: {doc.singapore_identity_id})")
                except Exception as e:
                    print(f"DEBUG: 验证保存结果时出错: {str(e)}")
                
                flash('更新成功！', 'success')
                
                # 获取当前的国家筛选参数
                country_id = request.args.get('country')
                # 构建重定向URL，保持筛选状态，并添加时间戳强制刷新
                redirect_url = url_for('visa_basic.visa_type_list')
                params = []
                if country_id:
                    params.append(f'country={country_id}')
                # 添加时间戳强制刷新
                params.append(f't={int(time.time())}')
                if params:
                    redirect_url += '?' + '&'.join(params)
                
                return redirect(redirect_url)
                
            except Exception as e:
                print(f"DEBUG: 处理POST请求时发生异常: {str(e)}")  # 调试信息
                print(f"DEBUG: 异常类型: {type(e)}")  # 调试信息
                import traceback
                print(f"DEBUG: 异常堆栈: {traceback.format_exc()}")  # 调试信息
                db.session.rollback()
                flash(f'更新失败：{str(e)}', 'error')
                return redirect(url_for('visa_basic.visa_type_list'))

        # GET 请求处理
        if field == 'identities':
            # 从 VisaDocuments 中获取当前身份选项
            current_documents = VisaDocuments.query.join(VisaTypes).filter(
                VisaTypes.visa_type == visa_type
            ).all()
            print(f"DEBUG: 找到 {len(current_documents)} 个当前文档")  # 调试信息
            
            current_identities = []
            for doc in current_documents:
                if doc.singapore_identity:
                    current_identities.append(doc.singapore_identity.identity_zh)
                    print(f"DEBUG: 当前身份: {doc.singapore_identity.identity_zh}")  # 调试信息
                else:
                    # 对于singapore_identity_id为None的记录，这通常是SHARE共用资料
                    current_identities.append('SHARE')
                    print(f"DEBUG: 当前身份: SHARE (共用资料)")  # 调试信息
            
            # 获取所有可用的身份选项（从 VisaSingaporeIdentity 表）
            all_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
            all_identities = [identity.identity_zh for identity in all_identities]
            # 添加SHARE选项
            all_identities.append('SHARE')
            print(f"DEBUG: 所有可用身份: {all_identities}")  # 调试信息
            print(f"DEBUG: 当前身份: {current_identities}")  # 调试信息
            
            field_name = '新加坡身份'
            return render_template('visas/edit_visa_type.html',
                               visa_type=visa_type,
                               field=field,
                               field_name=field_name,
                               current_value=current_identities,
                               all_identities=all_identities,
                               form=form)
        else:
            current_value = visa_type_record.fee if field == 'fee' else visa_type_record.processing_time
            field_name = '费用说明' if field == 'fee' else '处理时间'
            return render_template('visas/edit_visa_type.html',
                               visa_type=visa_type,
                               field=field,
                               field_name=field_name,
                               current_value=current_value,
                               form=form)
                               
    except Exception as e:
        flash(f'获取签证类型信息失败：{str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/visa/delete_visa_type/<visa_type>', methods=['POST'])
def delete_visa_type(visa_type):
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first_or_404()
        
        # 删除相关的文档记录
        VisaDocuments.query.join(VisaTypes).filter(VisaTypes.visa_type == visa_type).delete()
        
        # 删除签证类型记录
        db.session.delete(visa_type_record)
        db.session.commit()
        
        flash('签证类型删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    # 获取当前的国家筛选参数
    country_id = request.args.get('country')
    # 构建重定向URL，保持筛选状态
    redirect_url = url_for('visa_basic.visa_type_list')
    if country_id:
        redirect_url += f'?country={country_id}'
    
    return redirect(redirect_url)

""" about visa type end """

@visa_basic.route('/visa_home')
def visa_home():
    # 获取所有签证类型
    visa_categories = VisaTypes.query.all()
    
    # 在后端进行分组处理
    visas_by_country = {}
    for visa in visa_categories:
        country_name = visa.country.country_name_CN
        if country_name not in visas_by_country:
            visas_by_country[country_name] = []
        visas_by_country[country_name].append(visa)
    
    return render_template('visas/签证首页.html', 
                         visa_categories=visa_categories,
                         visas_by_country=visas_by_country)

@visa_basic.route('/test_data/<visa_type>')
def test_data(visa_type):
    """测试数据状态"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 检查VisaDocuments表中的数据
        documents = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        
        result = {
            'visa_type': {
                'id': visa_type_record.id,
                'name': visa_type_record.visa_type
            },
            'documents': []
        }
        
        for doc in documents:
            doc_info = {
                'id': doc.id,
                'visa_type_id': doc.visa_type_id,
                'singapore_identity_id': doc.singapore_identity_id,
                'document_info': doc.document_info,
                'additional_info': doc.additional_info
            }
            
            if doc.singapore_identity:
                doc_info['identity_name'] = doc.singapore_identity.identity_zh
            else:
                doc_info['identity_name'] = 'None (共用资料)'
            
            result['documents'].append(doc_info)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@visa_basic.route('/test_visa_data/<visa_type>')
def test_visa_data(visa_type):
    """测试签证类型数据"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': '签证类型不存在'})
        
        # 获取关联的文档
        docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        
        # 获取身份信息
        identities = []
        for doc in docs:
            if doc.singapore_identity_id:
                identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                if identity:
                    identities.append({
                        'id': identity.id,
                        'name': identity.identity_zh,
                        'doc_id': doc.id
                    })
        
        return jsonify({
            'visa_type': visa_type_record.visa_type,
            'visa_type_id': visa_type_record.id,
            'total_docs': len(docs),
            'identities': identities,
            'docs': [{'id': doc.id, 'identity_id': doc.singapore_identity_id} for doc in docs]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@visa_basic.route('/get_identity_options_with_share/<visa_type>')
def get_identity_options_with_share(visa_type):
    """获取包含SHARE身份的身份选项，用于编辑身份功能"""
    try:
        # URL解码签证类型
        from urllib.parse import unquote
        import html
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        print(f"获取身份选项 - 原始签证类型: '{visa_type}'")
        print(f"获取身份选项 - URL解码后: '{decoded_visa_type}'")
        
        # 验证签证类型是否存在
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            print(f"签证类型 '{decoded_visa_type}' 不存在")
            return jsonify({
                'success': False,
                'message': f'签证类型 {decoded_visa_type} 不存在',
                'identity_options': []
            }), 404
        
        # 从 VisaDocuments 表获取该签证类型实际已选择的身份
        selected_identities = db.session.query(VisaSingaporeIdentity.identity_zh)\
            .join(VisaDocuments, VisaDocuments.singapore_identity_id == VisaSingaporeIdentity.id)\
            .filter(VisaDocuments.visa_type_id == visa_type_record.id)\
            .distinct()\
            .all()
        
        # 将查询结果转换为列表
        identity_options = [identity[0] for identity in selected_identities]
        
        # 检查是否有SHARE记录（singapore_identity_id为None的记录）
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        # 如果存在SHARE记录且SHARE不在已选择的身份列表中，则添加
        if share_doc and 'SHARE' not in identity_options:
            identity_options.append('SHARE')
        
        print(f"从VisaDocuments表获取的当前已选择身份（包含SHARE）: {identity_options}")
        
        return jsonify({
            'success': True,
            'identity_options': identity_options
        })
    except Exception as e:
        print(f"获取身份选项时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'identity_options': []
        }), 500


@visa_basic.route('/get_all_identities_with_share')
def get_all_identities_with_share():
    """获取所有身份选项（包含SHARE），用于编辑身份功能"""
    try:
        # 从 VisaSingaporeIdentity 表获取所有身份（包括SHARE）
        identities = VisaSingaporeIdentity.query\
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
