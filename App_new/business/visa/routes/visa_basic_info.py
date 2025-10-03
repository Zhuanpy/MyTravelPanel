from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from pathlib import Path
from datetime import datetime
from App_new.exts import db, csrf
from App_new.business.visa.models.Visamodels import VisaCountries, VisaTypes, VisaSingaporeIdentity, VisaDocuments, VisaDocumentsList, VisaLinks
from App_new.utils.decorators import staff_only
from flask_wtf import FlaskForm
from wtforms import StringField
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
@login_required
@staff_only
@csrf.exempt
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
    return render_template('business/visa/签证身份管理/manage_identities.html', identities=identities)

@visa_basic.route('/delete_identity/<int:identity_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt  # 禁用CSRF保护
def delete_identity(identity_id):
    try:
        identity = VisaSingaporeIdentity.query.get_or_404(identity_id)
        db.session.delete(identity)
        db.session.commit()
        return jsonify({'success': True, 'message': '身份信息删除成功！'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})

@visa_basic.route('/edit_identity/<int:identity_id>', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt  # 禁用CSRF保护
def edit_identity(identity_id):
    try:
        identity = VisaSingaporeIdentity.query.get_or_404(identity_id)
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                identity_zh = request.form.get('identity_zh')
                identity_en = request.form.get('identity_en')
                remarks = request.form.get('remarks')
                
                print(f"DEBUG: 接收到的表单数据 - identity_zh: {identity_zh}, identity_en: {identity_en}, remarks: {remarks}")
                
                # 验证数据
                if not identity_zh or not identity_en:
                    error_msg = '中文名称和英文名称不能为空'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg})
                    else:
                        flash(error_msg, 'error')
                        return redirect(url_for('visa_basic.manage_identities'))
                
                # 更新数据
                identity.identity_zh = identity_zh
                identity.identity_en = identity_en
                identity.remarks = remarks
                
                print(f"DEBUG: 更新后的数据 - identity_zh: {identity.identity_zh}, identity_en: {identity.identity_en}, remarks: {identity.remarks}")
                
                db.session.commit()
                print("DEBUG: 数据库提交成功")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': '身份信息更新成功！'})
                else:
                    flash('身份信息更新成功！', 'success')
                    return redirect(url_for('visa_basic.manage_identities'))
                    
            except Exception as e:
                db.session.rollback()
                error_msg = f'更新失败：{str(e)}'
                print(f"DEBUG: 更新异常 - {error_msg}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg})
                else:
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_basic.manage_identities'))
        
        # GET 请求返回身份数据
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'success': True,
                'data': {
                    'id': identity.id,
                    'identity_zh': identity.identity_zh,
                    'identity_en': identity.identity_en,
                    'remarks': identity.remarks or ''
                }
            }
            print(f"DEBUG: 返回身份数据 - {data}")
            return jsonify(data)
        else:
            return render_template('business/visa/签证身份管理/manage_identities.html', 
                                 identities=VisaSingaporeIdentity.query.all(), 
                                 editing_identity=identity)
    except Exception as e:
        error_msg = f'路由异常：{str(e)}'
        print(f"DEBUG: 路由异常 - {error_msg}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('visa_basic.manage_identities'))

""" visa singapore  identity end """



""" visa  country start """

@visa_basic.route('/manage_countries', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
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

            # 处理国旗文件上传
            flag_file = None
            print(f"DEBUG: 添加国家 - 检查文件上传 - request.files: {list(request.files.keys())}")
            if 'flag_file' in request.files:
                flag_file_obj = request.files['flag_file']
                print(f"DEBUG: 添加国家 - 文件对象存在 - filename: {flag_file_obj.filename}")
                if flag_file_obj and flag_file_obj.filename:
                    # 获取文件扩展名
                    import os
                    from werkzeug.utils import secure_filename
                    
                    # 直接从原始文件名获取扩展名，避免secure_filename处理中文文件名的问题
                    original_filename = flag_file_obj.filename
                    file_ext = os.path.splitext(original_filename)[1].lower()
                    print(f"DEBUG: 添加国家 - 文件信息 - original: {original_filename}, ext: {file_ext}")
                    
                    # 检查文件类型
                    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
                    if file_ext in allowed_extensions:
                        # 生成新的文件名：国家代码 + 扩展名
                        new_filename = f"{country_code.lower()}{file_ext}"
                        print(f"DEBUG: 添加国家 - 新文件名 - {new_filename}")
                        
                        # 确保上传目录存在 - 使用Flask应用的静态文件夹路径
                        from flask import current_app
                        upload_dir = os.path.join(current_app.static_folder, 'images', 'flags')
                        os.makedirs(upload_dir, exist_ok=True)
                        print(f"DEBUG: 添加国家 - 上传目录 - {upload_dir}")
                        
                        # 保存文件
                        file_path = os.path.join(upload_dir, new_filename)
                        print(f"DEBUG: 添加国家 - 保存文件到 - {file_path}")
                        flag_file_obj.save(file_path)
                        flag_file = new_filename
                        print(f"DEBUG: 添加国家 - 国旗文件名 - {flag_file}")
                    else:
                        print(f"DEBUG: 添加国家 - 文件类型不支持 - {file_ext}")
                else:
                    print("DEBUG: 添加国家 - 文件对象为空或文件名为空")
            else:
                print("DEBUG: 添加国家 - 没有找到flag_file字段")

            # 创建新国家
            new_country = VisaCountries(
                country_name_CN=country_name_CN,
                country_name_EN=country_name_EN,
                country_code=country_code,
                flag_file=flag_file
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

    return render_template('business/visa/签证国家管理/manage_countries.html', countries=countries)

@visa_basic.route('/add_country', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def add_country():
    data = request.get_json()
    country = VisaCountries(
        country_name_CN=data['country_name_CN'],
        country_name_EN=data['country_name_EN'],
        country_code=data['country_code']
    )
    return add_to_db(country)

@visa_basic.route('/delete_country/<int:country_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt  # 禁用CSRF保护
def delete_country(country_id):
    try:
        country = VisaCountries.query.get_or_404(country_id)
        db.session.delete(country)
        db.session.commit()
        return jsonify({'success': True, 'message': '国家删除成功！'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})

@visa_basic.route('/edit_country/<int:country_id>', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt  # 禁用CSRF保护
def edit_country(country_id):
    try:
        country = VisaCountries.query.get_or_404(country_id)
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                country_name_CN = request.form.get('country_name_CN')
                country_name_EN = request.form.get('country_name_EN')
                country_code = request.form.get('country_code')
                
                print(f"DEBUG: 接收到的表单数据 - country_name_CN: {country_name_CN}, country_name_EN: {country_name_EN}, country_code: {country_code}")
                
                # 验证数据
                if not country_name_CN or not country_name_EN or not country_code:
                    error_msg = '所有字段都不能为空'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg})
                    else:
                        flash(error_msg, 'error')
                        return redirect(url_for('visa_basic.manage_countries'))
                
                # 处理国旗文件上传
                print(f"DEBUG: 检查文件上传 - request.files: {list(request.files.keys())}")
                if 'flag_file' in request.files:
                    flag_file_obj = request.files['flag_file']
                    print(f"DEBUG: 文件对象存在 - filename: {flag_file_obj.filename}")
                    if flag_file_obj and flag_file_obj.filename:
                        # 获取文件扩展名
                        import os
                        from werkzeug.utils import secure_filename
                        
                        # 直接从原始文件名获取扩展名，避免secure_filename处理中文文件名的问题
                        original_filename = flag_file_obj.filename
                        file_ext = os.path.splitext(original_filename)[1].lower()
                        print(f"DEBUG: 文件信息 - original: {original_filename}, ext: {file_ext}")
                        
                        # 检查文件类型
                        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
                        if file_ext in allowed_extensions:
                            # 删除旧的国旗文件
                            if country.flag_file:
                                from flask import current_app
                                old_file_path = os.path.join(current_app.static_folder, 'images', 'flags', country.flag_file)
                                print(f"DEBUG: 删除旧文件 - {old_file_path}")
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                            
                            # 生成新的文件名：国家代码 + 扩展名
                            new_filename = f"{country_code.lower()}{file_ext}"
                            print(f"DEBUG: 新文件名 - {new_filename}")
                            
                            # 确保上传目录存在 - 使用Flask应用的静态文件夹路径
                            from flask import current_app
                            upload_dir = os.path.join(current_app.static_folder, 'images', 'flags')
                            os.makedirs(upload_dir, exist_ok=True)
                            print(f"DEBUG: 上传目录 - {upload_dir}")
                            
                            # 保存文件
                            file_path = os.path.join(upload_dir, new_filename)
                            print(f"DEBUG: 保存文件到 - {file_path}")
                            flag_file_obj.save(file_path)
                            country.flag_file = new_filename
                            print(f"DEBUG: 国旗文件名已更新 - {country.flag_file}")
                        else:
                            print(f"DEBUG: 文件类型不支持 - {file_ext}")
                    else:
                        print("DEBUG: 文件对象为空或文件名为空")
                else:
                    print("DEBUG: 没有找到flag_file字段")
                
                # 更新数据
                country.country_name_CN = country_name_CN
                country.country_name_EN = country_name_EN
                country.country_code = country_code
                
                print(f"DEBUG: 更新后的数据 - country_name_CN: {country.country_name_CN}, country_name_EN: {country.country_name_EN}, country_code: {country.country_code}")
                
                db.session.commit()
                print("DEBUG: 数据库提交成功")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': '国家信息更新成功！'})
                else:
                    flash('国家信息更新成功！', 'success')
                    return redirect(url_for('visa_basic.manage_countries'))
                    
            except Exception as e:
                db.session.rollback()
                error_msg = f'更新失败：{str(e)}'
                print(f"DEBUG: 更新异常 - {error_msg}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg})
                else:
                    flash(error_msg, 'error')
                    return redirect(url_for('visa_basic.manage_countries'))
        
        # GET 请求返回国家数据
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'success': True,
                'data': {
                    'id': country.id,
                    'country_name_CN': country.country_name_CN,
                    'country_name_EN': country.country_name_EN,
                    'country_code': country.country_code,
                    'flag_file': country.flag_file
                }
            }
            print(f"DEBUG: 返回国家数据 - {data}")
            return jsonify(data)
        else:
            return render_template('business/visa/签证国家管理/manage_countries.html', 
                                 countries=VisaCountries.query.all(), 
                                 editing_country=country)
    except Exception as e:
        error_msg = f'路由异常：{str(e)}'
        print(f"DEBUG: 路由异常 - {error_msg}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('visa_basic.manage_countries'))

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
    query = VisaTypes.query.join(VisaCountries).order_by(
        VisaCountries.country_name_CN.asc(),
        VisaTypes.visa_type.asc()
    )
    
    # 应用国家筛选
    if country_id:
        query = query.filter(VisaTypes.country_id == country_id)
    
    # 获取分页数据
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    visa_types = pagination.items
    
    # 为每个签证类型获取实际的身份选项
    for vt in visa_types:
        # 从 visa_type_identities 表获取该签证类型的实际身份选项
        # 使用多对多关系直接获取
        actual_identities = [identity.identity_zh for identity in vt.identities]
        vt.actual_identities = actual_identities
    
    return render_template('business/visa/签证类型管理/visa_type_list.html', 
                         visa_types=visa_types,
                         countries=countries,
                         singapore_identities=singapore_identities,
                         pagination=pagination)

@visa_basic.route('/add_visa_type', methods=['GET', 'POST'])
@csrf.exempt
def add_visa_type():
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type = request.form.get('visa_type')
            processing_time = request.form.get('processing_time')
            fee = request.form.get('fee')
            introduction = request.form.get('introduction')
            country_id = request.form.get('country_id')
            identity_ids = request.form.getlist('identity_ids')  # 获取多个身份ID
            is_active = request.form.get('is_active') == 'on'  # 处理复选框值
            
            # 处理时间字段
            valid_until_str = request.form.get('valid_until')
            valid_until = None
            if valid_until_str:
                try:
                    valid_until = datetime.fromisoformat(valid_until_str.replace('T', ' '))
                except ValueError:
                    valid_until = None
            
            created_at_str = request.form.get('created_at')
            created_at = None
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('T', ' '))
                except ValueError:
                    created_at = None
            
            updated_at_str = request.form.get('updated_at')
            updated_at = None
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('T', ' '))
                except ValueError:
                    updated_at = None

            # 创建新的签证类型
            new_visa_type = VisaTypes(
                visa_type=visa_type,
                processing_time=processing_time,
                fee=fee,
                introduction=introduction,
                country_id=country_id,
                created_at=created_at,
                updated_at=updated_at,
                valid_until=valid_until,
                is_active=is_active
            )

            # 添加身份关联
            if identity_ids:
                identities = VisaSingaporeIdentity.query.filter(VisaSingaporeIdentity.id.in_(identity_ids)).all()
                
                # 1. 更新 visa_type_identities 表（多对多关系）
                for identity in identities:
                    new_visa_type.identities.append(identity)
                
                # 2. 更新 VisaDocuments 表
                for identity in identities:
                    new_doc = VisaDocuments(
                        visa_type_id=new_visa_type.id,
                        singapore_identity_id=identity.id
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

    # GET 请求处理 - 渲染添加页面
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    singapore_identities = VisaSingaporeIdentity.query\
        .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
        .order_by(VisaSingaporeIdentity.identity_zh)\
        .all()
    
    return render_template('business/visa/签证类型管理/visa_type_add.html', 
                         countries=countries,
                         singapore_identities=singapore_identities)

@visa_basic.route('/copy_visa_type', methods=['POST'])
@csrf.exempt
def copy_visa_type():
    """复制签证类型"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            source_visa_type = request.form.get('source_visa_type')
            new_visa_type = request.form.get('new_visa_type')
            processing_time = request.form.get('processing_time')
            fee = request.form.get('fee')
            introduction = request.form.get('introduction')
            country_id = request.form.get('country_id')
            identity_ids = request.form.getlist('identity_ids')
            is_active = request.form.get('is_active') == 'on'  # 处理复选框值
            
            # 处理时间字段
            valid_until_str = request.form.get('valid_until')
            valid_until = None
            if valid_until_str:
                try:
                    valid_until = datetime.fromisoformat(valid_until_str.replace('T', ' '))
                except ValueError:
                    valid_until = None
            
            created_at_str = request.form.get('created_at')
            created_at = None
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('T', ' '))
                except ValueError:
                    created_at = None
            
            updated_at_str = request.form.get('updated_at')
            updated_at = None
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('T', ' '))
                except ValueError:
                    updated_at = None
            
            # 检查源签证类型是否存在
            source_visa_type_record = VisaTypes.query.filter_by(visa_type=source_visa_type).first()
            if not source_visa_type_record:
                flash('源签证类型不存在', 'error')
                return redirect(url_for('visa_basic.visa_type_list'))
            
            # 检查新签证类型是否已存在
            existing_visa_type = VisaTypes.query.filter_by(visa_type=new_visa_type).first()
            if existing_visa_type:
                flash('签证类型名称已存在', 'error')
                return redirect(url_for('visa_basic.visa_type_list'))
            
            # 创建新的签证类型
            new_visa_type_record = VisaTypes(
                visa_type=new_visa_type,
                processing_time=processing_time,
                fee=fee,
                introduction=introduction,
                country_id=country_id,
                created_at=created_at,
                updated_at=updated_at,
                valid_until=valid_until,
                is_active=is_active
            )
            
            # 添加身份关联
            if identity_ids:
                identities = VisaSingaporeIdentity.query.filter(VisaSingaporeIdentity.id.in_(identity_ids)).all()
                
                # 1. 更新 visa_type_identities 表（多对多关系）
                for identity in identities:
                    new_visa_type_record.identities.append(identity)
                
                # 2. 更新 VisaDocuments 表
                for identity in identities:
                    new_doc = VisaDocuments(
                        visa_type_id=new_visa_type_record.id,
                        singapore_identity_id=identity.id
                    )
                    db.session.add(new_doc)
            
            # 创建签证类型对应的文件夹结构
            project_root = Path(__file__).resolve().parent.parent
            
            # 创建签证资源文件夹
            visa_resource_folder = project_root / "static" / "资源" / "签证" / new_visa_type
            visa_resource_folder.mkdir(parents=True, exist_ok=True)
            
            # 创建共用资料文件夹
            shared_folder = visa_resource_folder / "共用资料"
            shared_folder.mkdir(exist_ok=True)
            
            # 创建身份文件夹（PR、EP、SP等）
            for identity in identities:
                identity_folder = visa_resource_folder / identity.identity_zh
                identity_folder.mkdir(exist_ok=True)
            
            # 复制源签证类型的文档配置
            source_documents = VisaDocuments.query.filter_by(visa_type_id=source_visa_type_record.id).all()
            for source_doc in source_documents:
                new_doc = VisaDocuments(
                    visa_type_id=new_visa_type_record.id,
                    singapore_identity_id=source_doc.singapore_identity_id,
                    additional_info=source_doc.additional_info
                )
                db.session.add(new_doc)
            
            # 保存到数据库
            db.session.add(new_visa_type_record)
            db.session.commit()
            
            flash(f'签证类型"{new_visa_type}"复制成功！', 'success')
            return redirect(url_for('visa_basic.visa_type_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'复制失败: {str(e)}', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))
    
    return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/api/get_visa_type_data/<visa_type>')
def get_visa_type_data(visa_type):
    """获取签证类型数据用于复制"""
    try:
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        # 获取身份选项
        identities = [identity.identity_zh for identity in visa_type_record.identities]
        
        return jsonify({
            'success': True,
            'data': {
                'visa_type': visa_type_record.visa_type,
                'processing_time': visa_type_record.processing_time,
                'fee': visa_type_record.fee,
                'introduction': visa_type_record.introduction,
                'country_id': visa_type_record.country_id,
                'created_at': visa_type_record.created_at.isoformat() if visa_type_record.created_at else None,
                'updated_at': visa_type_record.updated_at.isoformat() if visa_type_record.updated_at else None,
                'valid_until': visa_type_record.valid_until.isoformat() if visa_type_record.valid_until else None,
                'identities': identities
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

class EditVisaTypeForm(FlaskForm):
    value = StringField('值', validators=[DataRequired()])

@visa_basic.route('/visa/edit_visa_type/<visa_type>/<field>', methods=['GET', 'POST'])
@csrf.exempt
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
                    
                    # 1. 更新 visa_type_identities 表（多对多关系）
                    try:
                        # 清空现有的身份关联
                        visa_type_record.identities.clear()
                        print(f"DEBUG: 清空现有身份关联")  # 调试信息
                        
                        # 添加新的身份关联
                        for identity_name in selected_identities:
                            if identity_name != 'SHARE':  # SHARE不存储在visa_type_identities表中
                                identity = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
                                if identity:
                                    visa_type_record.identities.append(identity)
                                    print(f"DEBUG: 添加到visa_type_identities: {identity_name} (ID: {identity.id})")  # 调试信息
                                else:
                                    print(f"DEBUG: 未找到身份: {identity_name}")  # 调试信息
                    except Exception as e:
                        print(f"DEBUG: 更新visa_type_identities表时出错: {str(e)}")  # 调试信息
                        raise e
                    
                    # 2. 更新 VisaDocuments 表
                    try:
                        # 删除现有的身份文档
                        docs_to_delete = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
                        print(f"DEBUG: 找到 {len(docs_to_delete)} 个要删除的文档")  # 调试信息
                        
                        for doc in docs_to_delete:
                            db.session.delete(doc)
                            print(f"DEBUG: 删除文档 ID: {doc.id}")  # 调试信息
                        
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
                    except Exception as e:
                        print(f"DEBUG: 更新VisaDocuments表时出错: {str(e)}")  # 调试信息
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
            form = EditVisaTypeForm()
            return render_template('business/visa/签证类型管理/edit_visa_type.html',
                               visa_type=visa_type,
                               field=field,
                               field_name=field_name,
                               current_value=current_identities,
                               all_identities=all_identities,
                               form=form)
        else:
            current_value = visa_type_record.fee if field == 'fee' else visa_type_record.processing_time
            field_name = '费用说明' if field == 'fee' else '处理时间'
            form = EditVisaTypeForm()
            return render_template('business/visa/签证类型管理/edit_visa_type.html',
                               visa_type=visa_type,
                               field=field,
                               field_name=field_name,
                               current_value=current_value,
                               form=form)
                               
    except Exception as e:
        flash(f'获取签证类型信息失败：{str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/visa/edit_visa_type_all/<visa_type>', methods=['POST'])
@csrf.exempt
def edit_visa_type_all(visa_type):
    """统一编辑签证类型的所有字段"""
    try:
        print(f"DEBUG: 开始处理统一编辑请求，visa_type={visa_type}")
        
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            flash('签证类型不存在', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))
        
        if request.method == 'POST':
            try:
                print(f"DEBUG: 开始处理POST请求")
                
                # 处理签证类型名称更新
                new_visa_type_name = request.form.get('visa_type_name')
                if new_visa_type_name and new_visa_type_name != visa_type:
                    # 检查新名称是否已存在
                    existing_visa_type = VisaTypes.query.filter_by(visa_type=new_visa_type_name).first()
                    if existing_visa_type:
                        flash('签证类型名称已存在', 'error')
                        return redirect(url_for('visa_basic.visa_type_list'))
                    
                    # 更新签证类型名称
                    visa_type_record.visa_type = new_visa_type_name
                    print(f"DEBUG: 更新签证类型名称为: {new_visa_type_name}")
                
                # 处理国家更新
                new_country_id = request.form.get('country_id')
                if new_country_id:
                    # 验证国家是否存在
                    country = VisaCountries.query.get(new_country_id)
                    if country:
                        visa_type_record.country_id = new_country_id
                        print(f"DEBUG: 更新国家为: {country.country_name_CN} (ID: {new_country_id})")
                    else:
                        flash('所选国家不存在', 'error')
                        return redirect(url_for('visa_basic.visa_type_list'))
                
                # 处理费用更新
                new_fee = request.form.get('fee')
                if new_fee:
                    visa_type_record.fee = new_fee
                    print(f"DEBUG: 更新费用为: {new_fee}")
                
                # 处理时间更新
                new_processing_time = request.form.get('processing_time')
                if new_processing_time:
                    visa_type_record.processing_time = new_processing_time
                    print(f"DEBUG: 更新处理时间为: {new_processing_time}")
                
                # 处理签证说明更新
                new_introduction = request.form.get('introduction')
                visa_type_record.introduction = new_introduction
                print(f"DEBUG: 更新签证说明为: {new_introduction}")
                
                # 处理激活状态更新
                is_active = request.form.get('is_active') == 'on'  # 处理复选框值
                visa_type_record.is_active = is_active
                print(f"DEBUG: 更新激活状态为: {is_active}")
                
                # 处理时间字段更新
                created_at_str = request.form.get('created_at')
                if created_at_str:
                    try:
                        visa_type_record.created_at = datetime.fromisoformat(created_at_str)
                        print(f"DEBUG: 更新创建时间为: {created_at_str}")
                    except ValueError:
                        print(f"DEBUG: 创建时间格式错误: {created_at_str}")
                
                updated_at_str = request.form.get('updated_at')
                if updated_at_str:
                    try:
                        visa_type_record.updated_at = datetime.fromisoformat(updated_at_str)
                        print(f"DEBUG: 更新更新时间为: {updated_at_str}")
                    except ValueError:
                        print(f"DEBUG: 更新时间格式错误: {updated_at_str}")
                
                valid_until_str = request.form.get('valid_until')
                if valid_until_str:
                    try:
                        visa_type_record.valid_until = datetime.fromisoformat(valid_until_str)
                        print(f"DEBUG: 更新有效期为: {valid_until_str}")
                    except ValueError:
                        print(f"DEBUG: 有效期格式错误: {valid_until_str}")
                
                # 处理身份选项更新
                selected_identities = request.form.getlist('identities')
                print(f"DEBUG: 选择的身份: {selected_identities}")
                print(f"DEBUG: 签证类型记录ID: {visa_type_record.id}")
                
                # 1. 更新 visa_type_identities 表（多对多关系）
                try:
                    # 清空现有的身份关联
                    visa_type_record.identities.clear()
                    print(f"DEBUG: 清空现有身份关联")
                    
                    # 添加新的身份关联
                    for identity_name in selected_identities:
                        if identity_name != 'SHARE':  # SHARE不存储在visa_type_identities表中
                            identity = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
                            if identity:
                                visa_type_record.identities.append(identity)
                                print(f"DEBUG: 添加到visa_type_identities: {identity_name} (ID: {identity.id})")
                            else:
                                print(f"DEBUG: 未找到身份: {identity_name}")
                except Exception as e:
                    print(f"DEBUG: 更新visa_type_identities表时出错: {str(e)}")
                    raise e
                
                # 2. 更新 VisaDocuments 表（智能更新，不删除已有配置）
                try:
                    # 获取现有的文档记录
                    existing_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
                    existing_identity_ids = {doc.singapore_identity_id for doc in existing_docs}
                    print(f"DEBUG: 现有文档记录: {len(existing_docs)} 个")
                    
                    # 获取SHARE身份ID
                    share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
                    share_identity_id = share_identity.id if share_identity else None
                    
                    # 构建新的身份ID集合
                    new_identity_ids = set()
                    for identity_name in selected_identities:
                        if identity_name == 'SHARE':
                            new_identity_ids.add(share_identity_id)
                        else:
                            identity = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
                            if identity:
                                new_identity_ids.add(identity.id)
                    
                    # 删除不再需要的身份文档
                    for doc in existing_docs:
                        if doc.singapore_identity_id not in new_identity_ids:
                            print(f"DEBUG: 删除不再需要的文档 ID: {doc.id}, 身份ID: {doc.singapore_identity_id}")
                            db.session.delete(doc)
                    
                    # 添加新的身份文档（只添加不存在的）
                    for identity_name in selected_identities:
                        try:
                            if identity_name == 'SHARE':
                                if share_identity_id not in existing_identity_ids:
                                    new_doc = VisaDocuments(
                                        visa_type_id=visa_type_record.id,
                                        singapore_identity_id=share_identity_id
                                    )
                                    db.session.add(new_doc)
                                    print(f"DEBUG: 添加SHARE文档")
                            else:
                                identity = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
                                if identity and identity.id not in existing_identity_ids:
                                    new_doc = VisaDocuments(
                                        visa_type_id=visa_type_record.id,
                                        singapore_identity_id=identity.id
                                    )
                                    db.session.add(new_doc)
                                    print(f"DEBUG: 添加身份文档: {identity_name} (ID: {identity.id})")
                        except Exception as e:
                            print(f"DEBUG: 添加身份文档时出错: {str(e)}")
                            continue
                except Exception as e:
                    print(f"DEBUG: 更新VisaDocuments表时出错: {str(e)}")
                    raise e
                
                # 提交所有更改
                db.session.commit()
                print(f"DEBUG: 数据库提交成功")
                
                flash('签证类型更新成功！', 'success')
                return redirect(url_for('visa_basic.visa_type_list'))
                
            except Exception as e:
                print(f"DEBUG: 处理POST请求时出错: {str(e)}")
                print(f"DEBUG: 异常类型: {type(e)}")
                import traceback
                print(f"DEBUG: 异常堆栈: {traceback.format_exc()}")
                db.session.rollback()
                flash(f'更新失败：{str(e)}', 'error')
                return redirect(url_for('visa_basic.visa_type_list'))
        
    except Exception as e:
        flash(f'获取签证类型信息失败：{str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/visa/delete_visa_type/<visa_type>', methods=['POST'])
@csrf.exempt
def delete_visa_type(visa_type):
    print(f"DEBUG: 开始删除签证类型: {visa_type}")
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            flash('签证类型不存在', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))
        
        print(f"DEBUG: 找到签证类型记录: ID={visa_type_record.id}")
        
        # 清空多对多关系
        visa_type_record.identities.clear()
        print(f"DEBUG: 清空了身份关联")
        
        # 删除相关的文档记录
        try:
            deleted_docs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).delete()
            print(f"DEBUG: 删除了 {deleted_docs} 个相关文档记录")
        except Exception as e:
            print(f"DEBUG: 删除文档记录时出错: {str(e)}")
        
        # 删除相关的链接记录
        try:
            deleted_links = VisaLinks.query.filter_by(visa_type_id=visa_type_record.id).delete()
            print(f"DEBUG: 删除了 {deleted_links} 个相关链接记录")
        except Exception as e:
            print(f"DEBUG: 删除链接记录时出错: {str(e)}")
        
        # 删除签证类型记录
        db.session.delete(visa_type_record)
        db.session.commit()
        print(f"DEBUG: 签证类型删除成功")
        
        flash('签证类型删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: 删除失败，错误: {str(e)}")
        import traceback
        print(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
        flash(f'删除失败：{str(e)}', 'error')
    
    # 获取当前的国家筛选参数
    country_id = request.args.get('country')
    # 构建重定向URL，保持筛选状态
    redirect_url = url_for('visa_basic.visa_type_list')
    if country_id:
        redirect_url += f'?country={country_id}'
    
    print(f"DEBUG: 重定向到: {redirect_url}")
    return redirect(redirect_url)

""" about visa type end """

@visa_basic.route('/visa_home')
@login_required
@staff_only
def visa_home():
    # 获取所有签证类型（只显示激活的）
    visa_categories = VisaTypes.query.filter_by(is_active=True).all()
    
    # 在后端进行分组处理
    visas_by_country = {}
    for visa in visa_categories:
        country_name = visa.country.country_name_CN
        if country_name not in visas_by_country:
            visas_by_country[country_name] = []
        visas_by_country[country_name].append(visa)
    
    return render_template('business/visa/签证首页.html', 
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
    """获取所有身份选项，包括SHARE"""
    try:
        # 获取所有身份
        identities = VisaSingaporeIdentity.query\
            .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
            .order_by(VisaSingaporeIdentity.identity_zh)\
            .all()
        
        # 转换为列表格式
        identity_list = [identity.to_dict() for identity in identities]
        
        # 添加SHARE选项
        identity_list.append({
            'id': None,
            'identity_zh': 'SHARE',
            'identity_en': 'SHARE',
            'remarks': '共用资料'
        })
        
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


# 签证文档管理器相关路由
@visa_basic.route('/visa_type_document_manager')
def visa_type_document_manager():
    """签证文档管理器主页面"""
    try:
        visa_type_param = request.args.get('visa_type')
        # 获取所有签证类型
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        # 获取所有文档
        documents = VisaDocumentsList.query.order_by(VisaDocumentsList.name).all()
        # 获取所有身份（SHARE排在第一位，其他按字母顺序）
        all_identities = VisaSingaporeIdentity.query.all()
        
        # 手动排序：SHARE排在第一位，其他按identity_zh排序
        identities = []
        share_identity = None
        
        for identity in all_identities:
            if identity.identity_zh == 'SHARE':
                share_identity = identity
            else:
                identities.append(identity)
        
        # 其他身份按字母顺序排序
        identities.sort(key=lambda x: x.identity_zh)
        
        # SHARE放在第一位
        if share_identity:
            identities.insert(0, share_identity)
        
        return render_template('business/visa/签证类型管理/visa_type_document_manager.html',
                             visa_types=visa_types,
                             documents=documents,
                             identities=identities,
                             selected_visa_type=visa_type_param)
    except Exception as e:
        flash(f'加载签证文档管理器时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))


@visa_basic.route('/api/get_visa_documents/<visa_type>')
def get_visa_documents(visa_type):
    """获取特定签证类型的文档配置，包括SHARE身份和实际关联身份"""
    try:
        print(f"DEBUG: 获取签证文档配置 - 签证类型: {visa_type}")
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            print(f"DEBUG: 签证类型不存在: {visa_type}")
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            })
        print(f"DEBUG: 找到签证类型记录 - ID: {visa_type_record.id}")
        
        # 获取所有文档配置记录
        visa_documents = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        print(f"DEBUG: 找到 {len(visa_documents)} 个文档配置记录")
        
        # 获取SHARE身份
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            print(f"DEBUG: 未找到SHARE身份记录")
            return jsonify({
                'success': False,
                'message': '未找到SHARE身份记录'
            })
        
        # 获取多对多关系中的身份
        linked_identities = visa_type_record.identities
        print(f"DEBUG: 找到 {len(linked_identities)} 个多对多关联身份")
        
        # 构建完整的身份列表（包括SHARE和关联身份）
        all_identities = [share_identity] + [identity for identity in linked_identities if identity.id != share_identity.id]
        print(f"DEBUG: 完整身份列表: {[i.identity_zh for i in all_identities]}")
        
        config_data = {
            'visa_type': visa_type,
            'documents': [],
            'identities': [ {'id': i.id, 'identity_zh': i.identity_zh} for i in all_identities ]
        }
        
        for identity in all_identities:
            print(f"DEBUG: 处理身份: {identity.identity_zh} (ID: {identity.id})")
            identity_docs = [vd for vd in visa_documents if vd.singapore_identity_id == identity.id]
            print(f"DEBUG: 找到 {len(identity_docs)} 个该身份的配置记录")
            
            selected_documents = []
            additional_info = ""
            applicant_additional_info = ""
            
            for vd in identity_docs:
                print(f"DEBUG: 处理配置记录 ID: {vd.id}")
                if vd.selected_documents:
                    print(f"DEBUG: 该配置有 {len(vd.selected_documents)} 个选中文档")
                    
                    # 查询关联表中的准备方信息
                    from sqlalchemy import text
                    sql = text("""
                        SELECT document_id, responsible_party 
                        FROM visa_document_documents 
                        WHERE visa_document_id = :visa_doc_id
                    """)
                    result = db.session.execute(sql, {'visa_doc_id': vd.id})
                    responsible_parties = {row.document_id: row.responsible_party for row in result}
                    
                    for doc in vd.selected_documents:
                        responsible_party = responsible_parties.get(doc.id, 'FOR_APPLICATION')
                        doc_info = {
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category,
                            'responsible_party': responsible_party
                        }
                        selected_documents.append(doc_info)
                        print(f"DEBUG: 添加文档: {doc.name} (ID: {doc.id}, 准备方: {responsible_party})")
                else:
                    print(f"DEBUG: 该配置没有选中文档")
                additional_info = vd.additional_info or ""
                applicant_additional_info = vd.applicant_additional_info or ""
            
            config_data['documents'].append({
                'singapore_identity_id': identity.id,
                'identity_name': identity.identity_zh,
                'selected_documents': selected_documents,
                'additional_info': additional_info,
                'applicant_additional_info': applicant_additional_info
            })
            print(f"DEBUG: 身份 {identity.identity_zh} 配置完成，选中文档数: {len(selected_documents)}")
        
        print(f"DEBUG: 最终配置数据:")
        print(f"  - 签证类型: {config_data['visa_type']}")
        print(f"  - 配置数量: {len(config_data['documents'])}")
        for doc_config in config_data['documents']:
            identity_name = doc_config['identity_name']
            doc_count = len(doc_config['selected_documents'])
            print(f"  - {identity_name}: {doc_count} 个文档")
            if doc_config['selected_documents']:
                doc_names = [d['name'] for d in doc_config['selected_documents']]
                print(f"    文档: {doc_names}")
        
        return jsonify({
            'success': True,
            'data': config_data
        })
    except Exception as e:
        print(f"获取签证文档配置时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取配置失败: {str(e)}'
        })


@visa_basic.route('/api/save_visa_documents/<visa_type>', methods=['POST'])
@csrf.exempt  # 禁用CSRF保护
def save_visa_documents(visa_type):
    """保存签证类型的文档配置 - 增量更新模式"""
    try:
        from flask import request
        
        print(f"DEBUG: 接收到的签证类型: '{visa_type}'")
        print(f"DEBUG: 请求方法: {request.method}")
        print(f"DEBUG: 请求头: {dict(request.headers)}")
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            print(f"DEBUG: 未找到签证类型: {visa_type}")
            return jsonify({
                'success': False,
                'message': f'签证类型不存在: {visa_type}'
            }), 400
        
        print(f"DEBUG: 找到签证类型记录: {visa_type_record.visa_type}")
        
        # 获取请求数据
        try:
            data = request.get_json()
            print(f"DEBUG: 接收到的请求数据: {data}")
        except Exception as json_error:
            print(f"DEBUG: JSON解析错误: {json_error}")
            return jsonify({
                'success': False,
                'message': f'JSON解析错误: {str(json_error)}'
            }), 400
        
        if not data:
            print("DEBUG: 请求数据为空")
            return jsonify({
                'success': False,
                'message': '请求数据为空'
            }), 400
        
        identity_configs = data.get('identity_configs', [])
        print(f"DEBUG: identity_configs: {identity_configs}")
        
        if not isinstance(identity_configs, list):
            print(f"DEBUG: identity_configs不是列表类型: {type(identity_configs)}")
            return jsonify({
                'success': False,
                'message': 'identity_configs必须是列表类型'
            }), 400
        
        # 获取现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=visa_type_record.id).all()
        existing_configs_dict = {config.singapore_identity_id: config for config in existing_configs}
        
        print(f"DEBUG: 找到 {len(existing_configs)} 个现有配置")
        print(f"DEBUG: 现有配置的identity_ids: {list(existing_configs_dict.keys())}")
        
        # 处理每个身份配置
        for i, config in enumerate(identity_configs):
            identity_id = config.get('identity_id')
            documents_data = config.get('documents', [])
            additional_info = config.get('additional_info', '')
            applicant_additional_info = config.get('applicant_additional_info', '')
            
            # 兼容旧的数据结构
            if not documents_data and 'document_ids' in config:
                document_ids = config.get('document_ids', [])
                documents_data = [{'document_id': doc_id, 'responsible_party': 'FOR_APPLICATION'} for doc_id in document_ids]
            
            print(f"DEBUG: 处理配置 {i+1} - identity_id: {identity_id} (类型: {type(identity_id)}), documents_data: {documents_data}")
            
            # 处理identity_id，SHARE身份使用SHARE身份ID，其他身份为整数
            processed_identity_id = None
            if identity_id == 'SHARE':
                # SHARE共用文档，使用SHARE身份ID
                share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
                if share_identity:
                    processed_identity_id = share_identity.id
                    print(f"DEBUG: 处理SHARE共用文档配置，使用SHARE身份ID: {processed_identity_id}")
                else:
                    # 如果SHARE身份不存在，创建一个
                    print(f"DEBUG: 未找到SHARE身份记录，正在创建...")
                    share_identity = VisaSingaporeIdentity(identity_zh='SHARE')
                    db.session.add(share_identity)
                    db.session.flush()  # 获取ID
                    processed_identity_id = share_identity.id
                    print(f"DEBUG: 创建SHARE身份记录，ID: {processed_identity_id}")
            elif identity_id is not None:
                try:
                    processed_identity_id = int(identity_id)
                except (ValueError, TypeError):
                    print(f"DEBUG: 无效的identity_id: {identity_id}")
                    continue
            else:
                # identity_id为null，表示SHARE共用文档
                share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
                if share_identity:
                    processed_identity_id = share_identity.id
                    print(f"DEBUG: 处理SHARE共用文档配置，使用SHARE身份ID: {processed_identity_id}")
                else:
                    # 如果SHARE身份不存在，创建一个
                    print(f"DEBUG: 未找到SHARE身份记录，正在创建...")
                    share_identity = VisaSingaporeIdentity(identity_zh='SHARE')
                    db.session.add(share_identity)
                    db.session.flush()  # 获取ID
                    processed_identity_id = share_identity.id
                    print(f"DEBUG: 创建SHARE身份记录，ID: {processed_identity_id}")
            
            print(f"DEBUG: 处理后的identity_id: {processed_identity_id} (类型: {type(processed_identity_id)})")
            
            # 查找或创建VisaDocuments记录
            if processed_identity_id in existing_configs_dict:
                # 更新现有记录
                visa_doc = existing_configs_dict[processed_identity_id]
                visa_doc.additional_info = additional_info
                visa_doc.applicant_additional_info = applicant_additional_info
                print(f"DEBUG: 更新现有配置 - ID: {visa_doc.id}")
            else:
                # 创建新记录
                visa_doc = VisaDocuments(
                    visa_type_id=visa_type_record.id,
                    singapore_identity_id=processed_identity_id,
                    additional_info=additional_info,
                    applicant_additional_info=applicant_additional_info
                )
                db.session.add(visa_doc)
                db.session.flush()  # 获取ID
                print(f"DEBUG: 创建新配置 - ID: {visa_doc.id}")
            
            # 更新选中的文档（多对多关系）
            if documents_data:
                # 清空现有的关联
                from sqlalchemy import text
                delete_sql = text("DELETE FROM visa_document_documents WHERE visa_document_id = :visa_doc_id")
                db.session.execute(delete_sql, {'visa_doc_id': visa_doc.id})
                
                # 添加新的关联，包含准备方信息
                for doc_data in documents_data:
                    doc_id = doc_data.get('document_id')
                    responsible_party = doc_data.get('responsible_party', 'FOR_APPLICATION')
                    
                    if doc_id:
                        insert_sql = text("""
                            INSERT INTO visa_document_documents (visa_document_id, document_id, responsible_party)
                            VALUES (:visa_doc_id, :doc_id, :responsible_party)
                        """)
                        db.session.execute(insert_sql, {
                            'visa_doc_id': visa_doc.id,
                            'doc_id': doc_id,
                            'responsible_party': responsible_party
                        })
                
                print(f"DEBUG: 为配置 {i+1} 设置了 {len(documents_data)} 个文档，包含准备方信息")
            else:
                # 如果没有选中文档，清空现有文档
                from sqlalchemy import text
                delete_sql = text("DELETE FROM visa_document_documents WHERE visa_document_id = :visa_doc_id")
                db.session.execute(delete_sql, {'visa_doc_id': visa_doc.id})
                print(f"DEBUG: 配置 {i+1} 没有选中文档，已清空")
        
        # 删除不再需要的配置（如果前端没有传递某个身份，说明要删除）
        existing_identity_ids = {config.singapore_identity_id for config in existing_configs}
        new_identity_ids = set()
        
        # 获取SHARE身份ID
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            # 如果SHARE身份不存在，创建一个
            print(f"DEBUG: 删除配置时未找到SHARE身份记录，正在创建...")
            share_identity = VisaSingaporeIdentity(identity_zh='SHARE')
            db.session.add(share_identity)
            db.session.flush()  # 获取ID
        share_identity_id = share_identity.id
        
        for config in identity_configs:
            identity_id = config.get('identity_id')
            if identity_id == 'SHARE':
                # SHARE共用文档，使用SHARE身份ID
                if share_identity_id:
                    new_identity_ids.add(share_identity_id)
            elif identity_id is not None:
                try:
                    new_identity_ids.add(int(identity_id))
                except (ValueError, TypeError):
                    pass
            else:
                # identity_id为null，表示SHARE共用文档
                if share_identity_id:
                    new_identity_ids.add(share_identity_id)
        
        to_delete_ids = existing_identity_ids - new_identity_ids
        
        for identity_id in to_delete_ids:
            if identity_id in existing_configs_dict:
                config_to_delete = existing_configs_dict[identity_id]
                db.session.delete(config_to_delete)
                identity_name = "SHARE共用文档" if identity_id == share_identity_id else f"身份ID: {identity_id}"
                print(f"DEBUG: 删除不再需要的配置 - {identity_name}")
        
        try:
            db.session.commit()
            print("DEBUG: 配置保存成功")
            
            return jsonify({
                'success': True,
                'message': f'{visa_type} 的文档配置已保存'
            })
        except Exception as commit_error:
            db.session.rollback()
            print(f"DEBUG: 提交数据库时发生错误: {str(commit_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'保存失败: {str(commit_error)}'
            }), 500
    except Exception as e:
        db.session.rollback()
        print(f"保存签证文档配置时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'保存失败: {str(e)}'
        }), 500


@visa_basic.route('/api/update_identity_documents/<visa_type>/<identity_id>', methods=['POST'])
@csrf.exempt
def update_identity_documents(visa_type, identity_id):
    """更新单个身份的文档配置 - 增量更新"""
    try:
        from flask import request
        
        print(f"DEBUG: 更新身份文档 - 签证类型: {visa_type}, 身份ID: {identity_id}")
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': f'签证类型不存在: {visa_type}'
            }), 400
        
        # 处理identity_id
        processed_identity_id = None
        if identity_id == 'SHARE':
            # SHARE共用文档，使用SHARE身份ID
            share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
            if share_identity:
                processed_identity_id = share_identity.id
                print(f"DEBUG: 处理SHARE共用文档，使用SHARE身份ID: {processed_identity_id}")
            else:
                return jsonify({
                    'success': False,
                    'message': '未找到SHARE身份记录'
                }), 400
        elif identity_id != 'null' and identity_id != 'undefined':
            try:
                processed_identity_id = int(identity_id)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的身份ID: {identity_id}'
                }), 400
        
        # 获取请求数据
        try:
            data = request.get_json()
            print(f"DEBUG: 接收到的数据: {data}")
        except Exception as json_error:
            return jsonify({
                'success': False,
                'message': f'JSON解析错误: {str(json_error)}'
            }), 400
        
        # 支持新的数据结构（包含准备方信息）
        documents_data = data.get('documents', [])
        additional_info = data.get('additional_info', '')
        
        # 兼容旧的数据结构
        if not documents_data and 'document_ids' in data:
            document_ids = data.get('document_ids', [])
            documents_data = [{'document_id': doc_id, 'responsible_party': 'FOR_APPLICATION'} for doc_id in document_ids]
        
        # 查找或创建VisaDocuments记录
        existing_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=processed_identity_id
        ).first()
        
        if existing_doc:
            # 更新现有记录
            existing_doc.additional_info = additional_info
            visa_doc = existing_doc
            print(f"DEBUG: 更新现有记录 - ID: {existing_doc.id}")
        else:
            # 创建新记录
            visa_doc = VisaDocuments(
                visa_type_id=visa_type_record.id,
                singapore_identity_id=processed_identity_id,
                additional_info=additional_info
            )
            db.session.add(visa_doc)
            db.session.flush()
            print(f"DEBUG: 创建新记录 - ID: {visa_doc.id}")
        
        # 更新选中的文档和准备方信息
        if documents_data:
            # 清空现有的关联
            visa_doc.selected_documents = []
            
            # 添加新的关联，包含准备方信息
            for doc_data in documents_data:
                doc_id = doc_data.get('document_id')
                responsible_party = doc_data.get('responsible_party', 'FOR_APPLICATION')
                
                if doc_id:
                    # 直接操作关联表，设置准备方信息
                    from sqlalchemy import text
                    sql = text("""
                        INSERT INTO visa_document_documents (visa_document_id, document_id, responsible_party)
                        VALUES (:visa_doc_id, :doc_id, :responsible_party)
                        ON DUPLICATE KEY UPDATE responsible_party = :responsible_party
                    """)
                    db.session.execute(sql, {
                        'visa_doc_id': visa_doc.id,
                        'doc_id': doc_id,
                        'responsible_party': responsible_party
                    })
            
            print(f"DEBUG: 设置了 {len(documents_data)} 个文档")
        else:
            visa_doc.selected_documents = []
            print(f"DEBUG: 清空了所有文档")
        
        db.session.commit()
        print(f"DEBUG: 身份文档更新成功")
        
        return jsonify({
            'success': True,
            'message': f'身份文档配置已更新'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"更新身份文档时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@visa_basic.route('/api/get_all_documents')
def get_all_documents():
    """获取所有可用文档"""
    try:
        documents = VisaDocumentsList.query.order_by(VisaDocumentsList.name).all()
        document_list = []
        
        for doc in documents:
            document_list.append({
                'id': doc.id,
                'name': doc.name,
                'category': doc.category,
                'description': doc.description
            })
        
        return jsonify({
            'success': True,
            'documents': document_list
        })
    except Exception as e:
        print(f"获取文档列表时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取文档列表失败: {str(e)}'
        })


@visa_basic.route('/api/get_all_visa_types')
def get_all_visa_types():
    """获取所有签证类型列表"""
    try:
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        visa_types_data = []
        for visa_type in visa_types:
            visa_types_data.append({
                'id': visa_type.id,
                'visa_type': visa_type.visa_type
            })
        
        return jsonify({
            'success': True,
            'visa_types': visa_types_data
        })
    except Exception as e:
        print(f"DEBUG: 获取签证类型列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取签证类型列表失败: {str(e)}'
        }), 500


@visa_basic.route('/api/copy_visa_documents/<visa_type>', methods=['POST'])
@csrf.exempt  # 禁用CSRF保护
def copy_visa_documents(visa_type):
    """复制签证类型的文档配置"""
    try:
        from flask import request
        
        print(f"DEBUG: 复制签证配置 - 目标签证类型: {visa_type}")
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'source_visa_type' not in data:
            return jsonify({
                'success': False,
                'message': '缺少源签证类型参数'
            }), 400
        
        source_visa_type = data['source_visa_type']
        print(f"DEBUG: 源签证类型: {source_visa_type}")
        
        # 获取目标签证类型
        target_visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not target_visa_type_record:
            return jsonify({
                'success': False,
                'message': f'目标签证类型不存在: {visa_type}'
            }), 400
        
        # 获取源签证类型
        source_visa_type_record = VisaTypes.query.filter_by(visa_type=source_visa_type).first()
        if not source_visa_type_record:
            return jsonify({
                'success': False,
                'message': f'源签证类型不存在: {source_visa_type}'
            }), 400
        
        # 检查是否复制自己
        if source_visa_type == visa_type:
            return jsonify({
                'success': False,
                'message': '不能复制自己的配置'
            }), 400
        
        print(f"DEBUG: 找到源签证类型记录 ID: {source_visa_type_record.id}")
        print(f"DEBUG: 找到目标签证类型记录 ID: {target_visa_type_record.id}")
        
        # 删除目标签证类型的所有现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=target_visa_type_record.id).all()
        print(f"DEBUG: 删除目标签证类型的 {len(existing_configs)} 个现有配置")
        
        for config in existing_configs:
            # 删除关联的文档记录
            from sqlalchemy import text
            db.session.execute(text("DELETE FROM visa_document_documents WHERE visa_document_id = :visa_doc_id"), 
                             {'visa_doc_id': config.id})
            db.session.delete(config)
        
        # 获取源签证类型的所有配置
        source_configs = VisaDocuments.query.filter_by(visa_type_id=source_visa_type_record.id).all()
        print(f"DEBUG: 找到源签证类型的 {len(source_configs)} 个配置")
        
        if not source_configs:
            return jsonify({
                'success': False,
                'message': f'源签证类型 "{source_visa_type}" 没有配置数据'
            }), 400
        
        # 复制配置
        copied_count = 0
        for source_config in source_configs:
            print(f"DEBUG: 复制配置 - 身份ID: {source_config.singapore_identity_id}")
            
            # 创建新的配置记录
            new_config = VisaDocuments(
                visa_type_id=target_visa_type_record.id,
                singapore_identity_id=source_config.singapore_identity_id,
                additional_info=source_config.additional_info
            )
            db.session.add(new_config)
            db.session.flush()  # 获取新记录的ID
            
            # 复制关联的文档
            if source_config.selected_documents:
                for doc in source_config.selected_documents:
                    # 查询原配置中该文档的准备方信息
                    result = db.session.execute(text("""
                        SELECT responsible_party 
                        FROM visa_document_documents 
                        WHERE visa_document_id = :visa_doc_id AND document_id = :doc_id
                    """), {'visa_doc_id': source_config.id, 'doc_id': doc.id})
                    
                    responsible_party = 'FOR_APPLICATION'  # 默认值
                    for row in result:
                        responsible_party = row.responsible_party
                        break
                    
                    # 插入新的关联记录
                    db.session.execute(text("""
                        INSERT INTO visa_document_documents (visa_document_id, document_id, responsible_party)
                        VALUES (:visa_doc_id, :doc_id, :responsible_party)
                    """), {
                        'visa_doc_id': new_config.id,
                        'doc_id': doc.id,
                        'responsible_party': responsible_party
                    })
                    
                    print(f"DEBUG: 复制文档 {doc.name} (ID: {doc.id}), 准备方: {responsible_party}")
            
            copied_count += 1
        
        # 提交事务
        db.session.commit()
        
        print(f"DEBUG: 复制完成，共复制了 {copied_count} 个身份配置")
        
        return jsonify({
            'success': True,
            'message': f'成功从 "{source_visa_type}" 复制了 {copied_count} 个身份配置到 "{visa_type}"'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: 复制配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'复制配置失败: {str(e)}'
        }), 500


@visa_basic.route('/visa/intro/<visa_type>')
def visa_intro(visa_type):
    """签证介绍页面"""
    try:
        # 获取签证类型信息
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            flash('签证类型不存在', 'error')
            return redirect(url_for('visa_basic.visa_home'))
        
        # 获取签证类型的基本信息
        types_info = {
            'fee': visa_type_record.fee or '费用信息正在更新中...',
            'processing_time': visa_type_record.processing_time or '处理时间信息正在更新中...'
        }
        
        # 获取相关链接（这里可以从数据库获取，暂时使用空列表）
        links = []
        
        # 获取近期项目（这里可以从数据库获取，暂时使用空列表）
        projects = []
        
        return render_template('business/visa/签证类型管理/签证介绍.html', 
                             visa_type=visa_type,
                             types_info=types_info,
                             links=links,
                             projects=projects)
                             
    except Exception as e:
        print(f"加载签证介绍页面时发生错误: {str(e)}")
        flash('加载签证介绍页面失败', 'error')
        return redirect(url_for('visa_basic.visa_home'))

@visa_basic.route('/visa_document_relations_manager')
def visa_document_relations_manager():
    """visa_document_documents 关联关系管理界面"""
    try:
        # 获取所有签证类型
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        # 获取所有文档
        documents = VisaDocumentsList.query.order_by(VisaDocumentsList.name).all()
        # 获取所有身份
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        # 获取所有国家
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        return render_template('business/visa/签证类型管理/visa_document_relations_manager.html',
                             visa_types=visa_types,
                             documents=documents,
                             identities=identities,
                             countries=countries)
    except Exception as e:
        flash(f'加载管理界面时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_home'))


@visa_basic.route('/api/get_document_relations')
def get_document_relations():
    """获取所有文档关联关系"""
    try:
        from sqlalchemy import text
        
        sql = text("""
            SELECT 
                vdd.visa_document_id,
                vdd.document_id,
                vdd.responsible_party,
                vt.visa_type,
                vc.country_name_CN,
                vsi.identity_zh,
                vdl.name as document_name,
                vdl.category as document_category
            FROM visa_document_documents vdd
            JOIN visa_documents_request vdr ON vdd.visa_document_id = vdr.id
            JOIN visa_types vt ON vdr.visa_type_id = vt.id
            JOIN visa_countries vc ON vt.country_id = vc.id
            LEFT JOIN visa_singapore_identity vsi ON vdr.singapore_identity_id = vsi.id
            JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
            ORDER BY vt.visa_type, vsi.identity_zh, vdl.name
        """)
        
        result = db.session.execute(sql)
        relations = []
        
        for row in result:
            relations.append({
                'visa_document_id': row.visa_document_id,
                'document_id': row.document_id,
                'responsible_party': row.responsible_party,
                'visa_type': row.visa_type,
                'country_name': row.country_name_CN,
                'identity_name': row.identity_zh or 'SHARE',
                'document_name': row.document_name,
                'document_category': row.document_category
            })
        
        return jsonify({
            'success': True,
            'relations': relations
        })
    except Exception as e:
        print(f"获取文档关联关系时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }), 500


@visa_basic.route('/api/update_document_relation', methods=['POST'])
@csrf.exempt
def update_document_relation():
    """更新单个文档关联关系"""
    try:
        from flask import request
        
        data = request.get_json()
        visa_document_id = data.get('visa_document_id')
        document_id = data.get('document_id')
        responsible_party = data.get('responsible_party')
        
        if not all([visa_document_id, document_id, responsible_party]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证responsible_party值
        if responsible_party not in ['FOR_APPLICATION', 'FOR_AGENT']:
            return jsonify({
                'success': False,
                'message': '无效的准备方值'
            }), 400
        
        # 更新数据库
        from sqlalchemy import text
        sql = text("""
            UPDATE visa_document_documents 
            SET responsible_party = :responsible_party
            WHERE visa_document_id = :visa_document_id AND document_id = :document_id
        """)
        
        db.session.execute(sql, {
            'responsible_party': responsible_party,
            'visa_document_id': visa_document_id,
            'document_id': document_id
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '更新成功'
        })
    except Exception as e:
        db.session.rollback()
        print(f"更新文档关联关系时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@visa_basic.route('/api/delete_document_relation', methods=['POST'])
@csrf.exempt
def delete_document_relation():
    """删除文档关联关系"""
    try:
        from flask import request
        
        data = request.get_json()
        visa_document_id = data.get('visa_document_id')
        document_id = data.get('document_id')
        
        if not all([visa_document_id, document_id]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 删除关联关系
        from sqlalchemy import text
        sql = text("""
            DELETE FROM visa_document_documents 
            WHERE visa_document_id = :visa_document_id AND document_id = :document_id
        """)
        
        result = db.session.execute(sql, {
            'visa_document_id': visa_document_id,
            'document_id': document_id
        })
        
        db.session.commit()
        
        if result.rowcount > 0:
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '记录不存在'
            }), 404
    except Exception as e:
        db.session.rollback()
        print(f"删除文档关联关系时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@visa_basic.route('/api/batch_update_responsible_party', methods=['POST'])
@csrf.exempt
def batch_update_responsible_party():
    """批量更新准备方"""
    try:
        from flask import request
        
        data = request.get_json()
        visa_type = data.get('visa_type')
        identity_name = data.get('identity_name')
        responsible_party = data.get('responsible_party')
        
        if not all([visa_type, responsible_party]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证responsible_party值
        if responsible_party not in ['FOR_APPLICATION', 'FOR_AGENT']:
            return jsonify({
                'success': False,
                'message': '无效的准备方值'
            }), 400
        
        # 获取签证类型ID
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 400
        
        # 获取身份ID
        identity_id = None
        if identity_name and identity_name != 'SHARE':
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=identity_name).first()
            if identity_record:
                identity_id = identity_record.id
        
        # 获取签证文档记录
        visa_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=identity_id
        ).first()
        
        if not visa_doc:
            return jsonify({
                'success': False,
                'message': '未找到对应的签证文档记录'
            }), 404
        
        # 批量更新
        from sqlalchemy import text
        sql = text("""
            UPDATE visa_document_documents 
            SET responsible_party = :responsible_party
            WHERE visa_document_id = :visa_document_id
        """)
        
        result = db.session.execute(sql, {
            'responsible_party': responsible_party,
            'visa_document_id': visa_doc.id
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'批量更新成功，影响 {result.rowcount} 条记录'
        })
    except Exception as e:
        db.session.rollback()
        print(f"批量更新准备方时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量更新失败: {str(e)}'
        }), 500

# 签证类型管理主页面
@visa_basic.route('/visa_type_management')
def visa_type_management():
    """签证类型管理主页面"""
    try:
        # 获取所有签证类型
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        
        # 为每个签证类型获取实际的身份选项
        for vt in visa_types:
            actual_identities = [identity.identity_zh for identity in vt.identities]
            vt.actual_identities = actual_identities
        
        return render_template('business/visa/签证类型管理/visa_type_management.html',
                             visa_types=visa_types)
    except Exception as e:
        flash(f'加载签证类型管理页面时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))


# 模板文件管理相关路由
@visa_basic.route('/visa_template_manager')
def visa_template_manager():
    """签证模板文件管理器主页面"""
    try:
        visa_type_param = request.args.get('visa_type')
        # 获取所有签证类型
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        # 获取所有身份（SHARE排在第一位，其他按字母顺序）
        all_identities = VisaSingaporeIdentity.query.all()
        
        # 手动排序：SHARE排在第一位，其他按identity_zh排序
        identities = []
        share_identity = None
        
        for identity in all_identities:
            if identity.identity_zh == 'SHARE':
                share_identity = identity
            else:
                identities.append(identity)
        
        # 其他身份按字母顺序排序
        identities.sort(key=lambda x: x.identity_zh)
        
        # SHARE放在第一位
        if share_identity:
            identities.insert(0, share_identity)
        
        # 将identities转换为可序列化的格式
        identities_json = []
        for identity in identities:
            identities_json.append({
                'id': identity.id,
                'identity_zh': identity.identity_zh,
                'identity_en': identity.identity_en
            })
        
        return render_template('business/visa/签证类型管理/visa_template_manager.html',
                             visa_types=visa_types,
                             identities=identities,
                             identities_json=identities_json,
                             selected_visa_type=visa_type_param)
    except Exception as e:
        flash(f'加载签证模板管理器时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))


@visa_basic.route('/api/visa_templates/get_templates', methods=['GET'])
def get_visa_templates():
    """获取指定签证类型的模板文件"""
    try:
        visa_type = request.args.get('visa_type')
        identity_id = request.args.get('identity_id', type=int)
        
        if not visa_type:
            return jsonify({'success': False, 'message': '签证类型参数缺失'})
        
        # 获取签证类型ID
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        # 获取模板文件
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        templates = VisaTemplateFiles.get_templates_by_visa_type(visa_type_record.id, identity_id)
        
        # 按类型分组
        templates_by_type = {}
        for template in templates:
            if template.template_type not in templates_by_type:
                templates_by_type[template.template_type] = []
            templates_by_type[template.template_type].append(template.to_dict())
        
        return jsonify({
            'success': True,
            'templates': templates_by_type,
            'visa_type_id': visa_type_record.id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取模板文件失败: {str(e)}'})


@visa_basic.route('/api/visa_templates/upload', methods=['POST'])
@csrf.exempt
def upload_visa_template():
    """上传签证模板文件"""
    try:
        visa_type_id = request.form.get('visa_type_id', type=int)
        identity_id = request.form.get('identity_id', type=int)  # 可以为None（共用模板）
        template_name = request.form.get('template_name')
        template_type = request.form.get('template_type')
        description = request.form.get('description', '')
        
        if not all([visa_type_id, template_name, template_type]):
            return jsonify({'success': False, 'message': '必填参数缺失'})
        
        # 检查文件
        if 'template_file' not in request.files:
            return jsonify({'success': False, 'message': '未选择文件'})
        
        file = request.files['template_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'})
        
        # 检查文件类型
        allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            return jsonify({'success': False, 'message': f'不支持的文件类型: {file_extension}'})
        
        # 保存文件
        from werkzeug.utils import secure_filename
        import os
        from pathlib import Path
        
        # 获取签证类型信息
        visa_type_record = VisaTypes.query.get(visa_type_id)
        if not visa_type_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        # 构建文件保存路径
        project_root = Path(__file__).resolve().parent.parent.parent
        template_dir = project_root / "static" / "资源" / "签证" / visa_type_record.visa_type / "模板文件"
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果有身份，创建身份子文件夹
        if identity_id:
            identity_record = VisaSingaporeIdentity.query.get(identity_id)
            if identity_record:
                template_dir = template_dir / identity_record.identity_zh
                template_dir.mkdir(exist_ok=True)
        else:
            # 共用模板
            template_dir = template_dir / "共用模板"
            template_dir.mkdir(exist_ok=True)
        
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        # 添加时间戳避免重名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_without_ext = filename.rsplit('.', 1)[0]
        ext = filename.rsplit('.', 1)[1] if '.' in filename else ''
        safe_filename = f"{name_without_ext}_{timestamp}.{ext}"
        
        file_path = template_dir / safe_filename
        file.save(str(file_path))
        
        # 保存到数据库
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        
        template_file = VisaTemplateFiles(
            visa_type_id=visa_type_id,
            singapore_identity_id=identity_id,
            template_name=template_name,
            template_type=template_type,
            file_path=str(file_path.relative_to(project_root / "static")),
            file_size=os.path.getsize(file_path),
            file_type=file_extension,
            description=description
        )
        
        db.session.add(template_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '模板文件上传成功',
            'template': template_file.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})


@visa_basic.route('/api/visa_templates/delete/<int:template_id>', methods=['DELETE'])
@csrf.exempt
def delete_visa_template(template_id):
    """删除签证模板文件"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        
        template = VisaTemplateFiles.query.get(template_id)
        if not template:
            return jsonify({'success': False, 'message': '模板文件不存在'})
        
        # 删除物理文件
        import os
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        file_path = project_root / "static" / template.file_path
        
        if file_path.exists():
            os.remove(file_path)
        
        # 删除数据库记录
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '模板文件删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


@visa_basic.route('/api/visa_templates/download/<int:template_id>')
def download_visa_template(template_id):
    """下载签证模板文件"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        
        template = VisaTemplateFiles.query.get(template_id)
        if not template:
            flash('模板文件不存在', 'error')
            return redirect(url_for('visa_basic.visa_template_manager'))
        
        # 构建文件路径
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        file_path = project_root / "static" / template.file_path
        
        if not file_path.exists():
            flash('文件不存在', 'error')
            return redirect(url_for('visa_basic.visa_template_manager'))
        
        # 返回文件
        from flask import send_file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"{template.template_name}.{template.file_type}"
        )
        
    except Exception as e:
        flash(f'下载失败: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_template_manager'))


@visa_basic.route('/api/visa_templates/get_template_types')
def get_template_types():
    """获取所有模板类型"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        template_types = VisaTemplateFiles.get_template_types()
        types_list = [t[0] for t in template_types if t[0]]
        return jsonify({'success': True, 'template_types': types_list})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取模板类型失败: {str(e)}'})


@visa_basic.route('/document_order_manager/<visa_type>')
def document_order_manager(visa_type):
    """文档顺序管理页面"""
    try:
        from urllib.parse import unquote
        import html
        
        # URL解码参数
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            flash('签证类型不存在', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))
        
        # 获取国家信息
        country = VisaCountries.query.get(visa_type_record.country_id)
        
        # 获取身份选项
        identities = []
        if visa_type_record.identities:
            identities = [identity.identity_zh for identity in visa_type_record.identities]
        
        # 导入必要的模型
        from App_new.business.visa.models.Visamodels import visa_document_documents, VisaDocumentsList
        
        # 获取所有申请人准备的文档（合并去重）
        all_documents = {}  # {document_id: {document_info, associations}}
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 获取SHARE共用资料
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=share_identity_id
        ).first()
        
        if share_doc:
            try:
                share_associations = db.session.query(visa_document_documents).filter_by(
                    visa_document_id=share_doc.id,
                    responsible_party='FOR_APPLICATION'
                ).order_by(visa_document_documents.c.display_order.asc()).all()
            except Exception:
                # 如果display_order字段不存在，使用原来的方法
                share_associations = db.session.query(visa_document_documents).filter_by(
                    visa_document_id=share_doc.id,
                    responsible_party='FOR_APPLICATION'
                ).all()
            
            for association in share_associations:
                doc = VisaDocumentsList.query.get(association.document_id)
                if doc and doc.id not in all_documents:
                    all_documents[doc.id] = {
                        'document': doc,
                        'associations': []
                    }
                
                if doc and doc.id in all_documents:
                    all_documents[doc.id]['associations'].append({
                        'visa_document_id': share_doc.id,
                        'identity_type': 'SHARE',
                        'display_order': getattr(association, 'display_order', 0) or 0
                    })
        
        # 获取其他身份的文档
        for identity in visa_type_record.identities:
            if identity.identity_zh != 'SHARE':
                specific_doc = VisaDocuments.query.filter_by(
                    visa_type_id=visa_type_record.id,
                    singapore_identity_id=identity.id
                ).first()
                
                if specific_doc:
                    try:
                        specific_associations = db.session.query(visa_document_documents).filter_by(
                            visa_document_id=specific_doc.id,
                            responsible_party='FOR_APPLICATION'
                        ).order_by(visa_document_documents.c.display_order.asc()).all()
                    except Exception:
                        # 如果display_order字段不存在，使用原来的方法
                        specific_associations = db.session.query(visa_document_documents).filter_by(
                            visa_document_id=specific_doc.id,
                            responsible_party='FOR_APPLICATION'
                        ).all()
                    
                    for association in specific_associations:
                        doc = VisaDocumentsList.query.get(association.document_id)
                        if doc and doc.id not in all_documents:
                            all_documents[doc.id] = {
                                'document': doc,
                                'associations': []
                            }
                        
                        if doc and doc.id in all_documents:
                            # 检查是否已经存在相同的visa_document_id关联
                            existing_assoc = next((a for a in all_documents[doc.id]['associations'] 
                                                 if a['visa_document_id'] == specific_doc.id), None)
                            if not existing_assoc:
                                all_documents[doc.id]['associations'].append({
                                    'visa_document_id': specific_doc.id,
                                    'identity_type': identity.identity_zh,
                                    'display_order': getattr(association, 'display_order', 0) or 0
                                })
        
        # 转换为列表格式，按当前的最大display_order排序
        documents_list = []
        for doc_id, doc_data in all_documents.items():
            # 获取该文档在所有身份中的最大display_order作为排序依据
            max_order = max([assoc['display_order'] for assoc in doc_data['associations']], default=0)
            documents_list.append({
                'document': doc_data['document'],
                'associations': doc_data['associations'],
                'current_order': max_order
            })
        
        # 按current_order排序
        documents_list.sort(key=lambda x: x['current_order'])
        
        return render_template('business/visa/签证类型管理/document_order_manager.html',
                             visa_type=visa_type_record,
                             country=country,
                             identities=identities,
                             documents=documents_list)
        
    except Exception as e:
        flash(f'加载文档顺序管理页面时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/api/get_document_details/<int:visa_type_id>')
def get_document_details(visa_type_id):
    """获取签证类型的文档详情"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaDocuments, VisaDocumentsList
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.get(visa_type_id)
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 404
        
        # 获取SHARE身份
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            return jsonify({
                'success': False,
                'message': '未找到SHARE身份记录'
            }), 404
        
        # 获取所有关联身份
        linked_identities = visa_type_record.identities
        all_identities = [share_identity] + [identity for identity in linked_identities if identity.id != share_identity.id]
        
        result_data = {
            'share_doc': None,
            'specific_docs': {}
        }
        
        # 处理SHARE身份
        share_docs = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_id, 
            singapore_identity_id=share_identity.id
        ).first()
        
        if share_docs:
            documents = []
            if share_docs.selected_documents:
                for doc in share_docs.selected_documents:
                    documents.append({
                        'id': doc.id,
                        'name': doc.name,
                        'category': doc.category
                    })
            result_data['share_doc'] = {
                'visa_document_id': share_docs.id,
                'documents': documents
            }
        
        # 处理其他身份
        for identity in linked_identities:
            if identity.id != share_identity.id:
                identity_docs = VisaDocuments.query.filter_by(
                    visa_type_id=visa_type_id,
                    singapore_identity_id=identity.id
                ).first()
                
                if identity_docs:
                    documents = []
                    if identity_docs.selected_documents:
                        for doc in identity_docs.selected_documents:
                            documents.append({
                                'id': doc.id,
                                'name': doc.name,
                                'category': doc.category
                            })
                    result_data['specific_docs'][identity.identity_zh] = {
                        'visa_document_id': identity_docs.id,
                        'documents': documents
                    }
        
        return jsonify({
            'success': True,
            'data': result_data
        })
        
    except Exception as e:
        print(f"获取文档详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取文档详情失败: {str(e)}'
        }), 500

@visa_basic.route('/visa_type_detail/<visa_type>')
def visa_type_detail(visa_type):
    """签证类型详细页面"""
    try:
        # 获取签证类型信息
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            flash('签证类型不存在', 'error')
            return redirect(url_for('visa_basic.visa_type_list'))
        
        # 获取身份选项
        actual_identities = [identity.identity_zh for identity in visa_type_record.identities]
        visa_type_record.actual_identities = actual_identities
        
        # 获取文档配置信息
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaDocumentsList
        document_data = {}
        
        # 获取共用资料
        share_info = VisaDocuments.get_document_info(visa_type_record.id, None)
        document_data['SHARE'] = share_info
        
        # 获取各身份的文档配置
        for identity in visa_type_record.identities:
            info = VisaDocuments.get_document_info(visa_type_record.id, identity.id)
            document_data[identity.identity_zh] = info
        
        # 获取模板文件
        try:
            from App_new.business.visa.models.Visamodels import VisaTemplateFiles
            template_files = VisaTemplateFiles.get_templates_by_visa_type(visa_type_record.id)
            template_files = [template.to_dict() for template in template_files]
        except Exception as e:
            print(f"获取模板文件时出错: {str(e)}")
            template_files = []
        
        # 获取统计信息
        # 文档统计 - 计算文档信息中的项目数量
        total_documents = 0
        for data in document_data.values():
            if data and isinstance(data, dict) and 'document_info' in data:
                # 计算文档信息中的项目数量（按行分割，排除标题行）
                doc_lines = data['document_info'].split('\n')
                for line in doc_lines:
                    if line.strip().startswith('•') and not line.strip().startswith('• 暂无'):
                        total_documents += 1
        
        # 模板统计
        total_templates = len(template_files)
        
        # 项目统计（如果有项目相关的模型）
        try:
            from App_new.business.visa.models.Visamodels import VisaProject
            total_projects = VisaProject.query.filter_by(visa_type=visa_type).count()
        except:
            total_projects = 0
        
        # 统计数据
        document_stats = {'total_documents': total_documents}
        template_stats = {'total_templates': total_templates}
        project_stats = {'total_projects': total_projects}
        
        return render_template('business/visa/签证类型管理/visa_type_detail.html',
                             visa_type=visa_type_record,
                             document_data=document_data,
                             template_files=template_files,
                             document_stats=document_stats,
                             template_stats=template_stats,
                             project_stats=project_stats)
                             
    except Exception as e:
        flash(f'加载签证类型详情时出错: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))


@visa_basic.route('/api/get_all_documents_for_sorting/<int:visa_type_id>')
def get_all_documents_for_sorting(visa_type_id):
    """获取所有身份的资料并合并去重，用于统一排序"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaDocuments, VisaSingaporeIdentity, visa_document_documents, VisaDocumentsList
        
        # 验证签证类型是否存在
        visa_type = VisaTypes.query.get(visa_type_id)
        if not visa_type:
            return jsonify({'success': False, 'message': '签证类型不存在'}), 404
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 收集所有申请人准备的文档，按文档ID去重
        all_documents = {}  # {document_id: {document_info, associations}}
        
        # 获取SHARE共用资料
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_id,
            singapore_identity_id=share_identity_id
        ).first()
        
        if share_doc:
            share_associations = db.session.query(visa_document_documents).filter_by(
                visa_document_id=share_doc.id,
                responsible_party='FOR_APPLICATION'
            ).all()
            
            for association in share_associations:
                doc = VisaDocumentsList.query.get(association.document_id)
                if doc and doc.id not in all_documents:
                    all_documents[doc.id] = {
                        'document': {
                            'id': doc.id,
                            'name': doc.name
                        },
                        'associations': []
                    }
                
                if doc and doc.id in all_documents:
                    all_documents[doc.id]['associations'].append({
                        'visa_document_id': share_doc.id,
                        'identity_type': 'SHARE',
                        'display_order': association.display_order or 0
                    })
        
        # 获取其他身份的文档
        for identity in visa_type.identities:
            if identity.identity_zh != 'SHARE':
                specific_doc = VisaDocuments.query.filter_by(
                    visa_type_id=visa_type_id,
                    singapore_identity_id=identity.id
                ).first()
                
                if specific_doc:
                    specific_associations = db.session.query(visa_document_documents).filter_by(
                        visa_document_id=specific_doc.id,
                        responsible_party='FOR_APPLICATION'
                    ).all()
                    
                    for association in specific_associations:
                        doc = VisaDocumentsList.query.get(association.document_id)
                        if doc and doc.id not in all_documents:
                            all_documents[doc.id] = {
                                'document': {
                                    'id': doc.id,
                                    'name': doc.name
                                },
                                'associations': []
                            }
                        
                        if doc and doc.id in all_documents:
                            # 检查是否已经存在相同的visa_document_id关联
                            existing_assoc = next((a for a in all_documents[doc.id]['associations'] 
                                                 if a['visa_document_id'] == specific_doc.id), None)
                            if not existing_assoc:
                                all_documents[doc.id]['associations'].append({
                                    'visa_document_id': specific_doc.id,
                                    'identity_type': identity.identity_zh,
                                    'display_order': association.display_order or 0
                                })
        
        # 转换为列表格式，按当前的最大display_order排序
        documents_list = []
        for doc_id, doc_data in all_documents.items():
            # 获取该文档在所有身份中的最大display_order作为排序依据
            max_order = max([assoc['display_order'] for assoc in doc_data['associations']], default=0)
            documents_list.append({
                'document': doc_data['document'],
                'associations': doc_data['associations'],
                'current_order': max_order
            })
        
        # 按current_order排序
        documents_list.sort(key=lambda x: x['current_order'])
        
        return jsonify({
            'success': True, 
            'data': {
                'documents': documents_list,
                'visa_type_id': visa_type_id
            }
        })
        
    except Exception as e:
        print(f"获取所有文档失败: {str(e)}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500

@visa_basic.route('/api/update_all_documents_order/<int:visa_type_id>', methods=['POST'])
@csrf.exempt
def update_all_documents_order(visa_type_id):
    """更新所有文档的显示顺序，应用到所有相关的visa_document_documents记录"""
    try:
        data = request.get_json()
        if not data or 'document_orders' not in data:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        document_orders = data['document_orders']  # 格式: [{'document_id': 1, 'new_order': 0}, ...]
        
        # 验证签证类型是否存在
        visa_type = VisaTypes.query.get(visa_type_id)
        if not visa_type:
            return jsonify({'success': False, 'message': '签证类型不存在'}), 404
        
        # 更新文档顺序
        from sqlalchemy import text
        for order_item in document_orders:
            document_id = order_item.get('document_id')
            new_order = order_item.get('new_order')
            
            if document_id is None or new_order is None:
                continue
            
            # 更新该文档在所有visa_document_documents记录中的display_order
            update_sql = text("""
                UPDATE visa_document_documents 
                SET display_order = :new_order 
                WHERE document_id = :document_id
                AND responsible_party = 'FOR_APPLICATION'
            """)
            
            db.session.execute(update_sql, {
                'new_order': new_order,
                'document_id': document_id
            })
        
        db.session.commit()
        return jsonify({'success': True, 'message': '文档顺序更新成功'})
        
    except Exception as e:
        db.session.rollback()
        print(f"更新文档顺序时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes is None:
        return "未知"
    
    if size_bytes == 0:
        return "0 Bytes"
    
    size_names = ["Bytes", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# 注册模板过滤器
@visa_basic.app_template_filter('filesizeformat')
def filesizeformat_filter(size_bytes):
    """模板过滤器：格式化文件大小"""
    return format_file_size(size_bytes)


# 套用模板相关API
@visa_basic.route('/api/get_template_visa_types')
def get_template_visa_types():
    """获取可用的签证类型模板列表"""
    try:
        visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
        visa_type_names = [vt.visa_type for vt in visa_types]
        return jsonify({'success': True, 'visa_types': visa_type_names})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取签证类型列表失败: {str(e)}'})


@visa_basic.route('/api/get_template_preview')
def get_template_preview():
    """获取模板签证类型的预览信息"""
    try:
        visa_type = request.args.get('visa_type')
        if not visa_type:
            return jsonify({'success': False, 'message': '签证类型参数缺失'})
        
        # 获取签证类型信息
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        # 获取身份信息
        identities = [identity.identity_zh for identity in visa_type_record.identities]
        
        # 获取文档配置数量
        from App_new.business.visa.models.Visamodels import VisaDocuments
        document_count = 0
        # 计算共用资料
        share_info = VisaDocuments.get_document_info(visa_type_record.id, None)
        if share_info and share_info.get('document_info'):
            doc_lines = share_info['document_info'].split('\n')
            for line in doc_lines:
                if line.strip().startswith('•') and not line.strip().startswith('• 暂无'):
                    document_count += 1
        
        # 计算各身份的文档
        for identity in visa_type_record.identities:
            info = VisaDocuments.get_document_info(visa_type_record.id, identity.id)
            if info and info.get('document_info'):
                doc_lines = info['document_info'].split('\n')
                for line in doc_lines:
                    if line.strip().startswith('•') and not line.strip().startswith('• 暂无'):
                        document_count += 1
        
        # 获取模板文件数量
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        template_count = VisaTemplateFiles.query.filter_by(visa_type_id=visa_type_record.id, is_active=True).count()
        
        return jsonify({
            'success': True,
            'identities': identities,
            'document_count': document_count,
            'template_count': template_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取模板预览失败: {str(e)}'})


@visa_basic.route('/api/apply_template', methods=['POST'])
@csrf.exempt
def apply_template():
    """套用签证类型模板"""
    try:
        data = request.get_json()
        target_visa_type = data.get('target_visa_type')
        template_visa_type = data.get('template_visa_type')
        copy_documents = data.get('copy_documents', False)
        copy_templates = data.get('copy_templates', False)
        copy_identities = data.get('copy_identities', False)
        
        if not all([target_visa_type, template_visa_type]):
            return jsonify({'success': False, 'message': '参数缺失'})
        
        # 获取目标签证类型和模板签证类型
        target_record = VisaTypes.query.filter_by(visa_type=target_visa_type).first()
        template_record = VisaTypes.query.filter_by(visa_type=template_visa_type).first()
        
        if not target_record or not template_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTemplateFiles
        
        # 复制身份配置
        if copy_identities:
            # 清除目标签证类型的现有身份关联
            target_record.identities.clear()
            
            # 复制模板签证类型的身份关联
            for identity in template_record.identities:
                target_record.identities.append(identity)
        
        # 复制文档配置
        if copy_documents:
            # 获取模板签证类型的所有文档配置
            template_documents = VisaDocuments.query.filter_by(visa_type_id=template_record.id).all()
            
            # 删除目标签证类型的现有文档配置
            VisaDocuments.query.filter_by(visa_type_id=target_record.id).delete()
            
            # 复制文档配置
            for doc in template_documents:
                new_doc = VisaDocuments(
                    visa_type_id=target_record.id,
                    singapore_identity_id=doc.singapore_identity_id,
                    additional_info=doc.additional_info
                )
                # 复制选中的文档关系
                if doc.selected_documents:
                    for selected_doc in doc.selected_documents:
                        new_doc.selected_documents.append(selected_doc)
                db.session.add(new_doc)
        
        # 复制模板文件
        if copy_templates:
            # 获取模板签证类型的所有模板文件
            template_files = VisaTemplateFiles.query.filter_by(visa_type_id=template_record.id, is_active=True).all()
            
            # 删除目标签证类型的现有模板文件
            VisaTemplateFiles.query.filter_by(visa_type_id=target_record.id).delete()
            
            # 复制模板文件记录
            for template in template_files:
                new_template = VisaTemplateFiles(
                    visa_type_id=target_record.id,
                    singapore_identity_id=template.singapore_identity_id,
                    template_name=template.template_name,
                    template_type=template.template_type,
                    file_path=template.file_path,
                    file_size=template.file_size,
                    file_type=template.file_type,
                    description=template.description,
                    is_active=template.is_active
                )
                db.session.add(new_template)
        
        # 提交所有更改
        db.session.commit()
        
        return jsonify({'success': True, 'message': '模板套用成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'套用模板失败: {str(e)}'})

@visa_basic.route('/visa/toggle_active_status/<visa_type>', methods=['POST'])
@csrf.exempt
def toggle_active_status(visa_type):
    """切换签证类型的激活状态"""
    try:
        # 获取签证类型记录
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'success': False, 'message': '签证类型不存在'})
        
        # 获取请求数据
        data = request.get_json()
        new_status = data.get('is_active', not visa_type_record.is_active)
        
        # 更新激活状态
        visa_type_record.is_active = new_status
        
        # 如果激活，自动设置有效期为一年后
        if new_status:
            from datetime import datetime, timedelta
            visa_type_record.valid_until = datetime.utcnow() + timedelta(days=365)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'激活状态已更新为{"激活" if new_status else "未激活"}',
            'is_active': new_status,
            'valid_until': visa_type_record.valid_until.isoformat() if visa_type_record.valid_until else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@visa_basic.route('/visa_visit_stats')
@login_required
@staff_only
def visa_visit_stats():
    """签证访问统计页面"""
    try:
        from App_new.business.visa.models.Visamodels import VisaVisitStats
        
        # 获取查询参数
        days = request.args.get('days', 30, type=int)
        visa_type_id = request.args.get('visa_type_id', type=int)
        
        # 获取访问统计
        visit_stats = VisaVisitStats.get_visit_stats(visa_type_id=visa_type_id, days=days)
        
        # 获取热门签证
        popular_visas = VisaVisitStats.get_popular_visas(limit=20, days=days)
        
        # 获取所有签证类型（用于筛选）
        all_visa_types = VisaTypes.query.filter_by(is_active=True).order_by(VisaTypes.visa_type).all()
        
        # 统计数据
        total_visits = len(visit_stats)
        unique_visitors = len(set(stat.session_id for stat in visit_stats if stat.session_id))
        
        return render_template('business/visa/访问统计/visa_visit_stats.html',
                             visit_stats=visit_stats,
                             popular_visas=popular_visas,
                             all_visa_types=all_visa_types,
                             total_visits=total_visits,
                             unique_visitors=unique_visitors,
                             days=days,
                             selected_visa_type_id=visa_type_id)
                             
    except Exception as e:
        flash(f'加载访问统计失败: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/api/visa_visit_stats_data')
@login_required
@staff_only
def visa_visit_stats_data():
    """获取访问统计数据API"""
    try:
        from App_new.business.visa.models.Visamodels import VisaVisitStats
        from datetime import datetime, timedelta
        
        days = request.args.get('days', 30, type=int)
        visa_type_id = request.args.get('visa_type_id', type=int)
        
        # 获取访问统计
        visit_stats = VisaVisitStats.get_visit_stats(visa_type_id=visa_type_id, days=days)
        
        # 按日期分组统计
        daily_stats = {}
        for stat in visit_stats:
            date_key = stat.visit_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = 0
            daily_stats[date_key] += 1
        
        # 转换为列表格式
        chart_data = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            date_key = date.isoformat()
            chart_data.append({
                'date': date_key,
                'visits': daily_stats.get(date_key, 0)
            })
        
        chart_data.reverse()  # 按时间正序排列
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'total_visits': len(visit_stats),
            'unique_visitors': len(set(stat.session_id for stat in visit_stats if stat.session_id))
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取统计数据失败: {str(e)}'})

@visa_basic.route('/universal_visit_stats')
@login_required
@staff_only
def universal_visit_stats():
    """通用产品访问统计页面"""
    try:
        from App_new.shared.services.visit_stats_service import VisitStatsService
        
        # 获取查询参数
        days = request.args.get('days', 30, type=int)
        product_type = request.args.get('product_type', '')
        product_id = request.args.get('product_id', type=int)
        
        # 获取访问统计
        visit_stats = VisitStatsService.get_product_stats(product_type=product_type, days=days)
        
        # 获取热门产品
        popular_products = VisitStatsService.get_popular_products(product_type=product_type, limit=20, days=days)
        
        # 获取整体统计
        stats_summary = VisitStatsService.get_overall_stats(days=days)
        
        # 产品类型名称映射
        product_type_names = {
            'visa': '签证',
            'tour': '旅游',
            'flight': '机票',
            'hotel': '酒店',
            'package': '套餐'
        }
        
        return render_template('business/visa/访问统计/universal_visit_stats.html',
                             visit_stats=visit_stats,
                             popular_products=popular_products,
                             stats_summary=stats_summary,
                             product_type_names=product_type_names,
                             days=days,
                             selected_product_type=product_type,
                             selected_product_id=product_id)
                             
    except Exception as e:
        flash(f'加载访问统计失败: {str(e)}', 'error')
        return redirect(url_for('visa_basic.visa_type_list'))

@visa_basic.route('/api/universal_visit_stats_data')
@login_required
@staff_only
def universal_visit_stats_data():
    """获取通用访问统计数据API"""
    try:
        from App_new.shared.services.visit_stats_service import VisitStatsService
        from datetime import datetime, timedelta
        
        days = request.args.get('days', 30, type=int)
        product_type = request.args.get('product_type', '')
        product_id = request.args.get('product_id', type=int)
        
        # 获取访问统计
        visit_stats = VisitStatsService.get_product_stats(product_type=product_type, days=days)
        
        # 按日期分组统计
        daily_stats = {}
        for stat in visit_stats:
            date_key = stat.visit_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = 0
            daily_stats[date_key] += 1
        
        # 转换为列表格式
        chart_data = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            date_key = date.isoformat()
            chart_data.append({
                'date': date_key,
                'visits': daily_stats.get(date_key, 0)
            })
        
        chart_data.reverse()  # 按时间正序排列
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'total_visits': len(visit_stats),
            'unique_visitors': len(set(stat.session_id for stat in visit_stats if stat.session_id))
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取统计数据失败: {str(e)}'})
