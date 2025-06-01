from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from ..exts import db
from ..models import VisaCountries, VisaTypes, VisaSingaporeIdentity, VisaDocuments
from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField
from wtforms.validators import DataRequired

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
    singapore_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
    
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
        actual_identities = db.session.query(VisaDocuments.singapore_identity)\
            .filter(VisaDocuments.visa_type == vt.visa_type)\
            .filter(VisaDocuments.singapore_identity != 'SHARE')\
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
                        visa_type=visa_type,
                        singapore_identity=identity.identity_zh,
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
    singapore_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
    
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
                if field == 'identities':
                    # 处理身份选项更新
                    selected_identities = request.form.getlist('identities')
                    # 删除现有的身份文档
                    VisaDocuments.query.filter_by(visa_type=visa_type).delete()
                    # 添加新的身份文档
                    for identity in selected_identities:
                        new_doc = VisaDocuments(
                            visa_type=visa_type,
                            singapore_identity=identity
                        )
                        db.session.add(new_doc)
                else:
                    # 更新费用或处理时间
                    value = request.form.get('value')
                    if field == 'fee':
                        visa_type_record.fee = value
                    else:  # processing_time
                        visa_type_record.processing_time = value

                db.session.commit()
                flash('更新成功！', 'success')
                
                # 获取当前的国家筛选参数
                country_id = request.args.get('country')
                # 构建重定向URL，保持筛选状态
                redirect_url = url_for('visa_basic.visa_type_list')
                if country_id:
                    redirect_url += f'?country={country_id}'
                
                return redirect(redirect_url)
                
            except Exception as e:
                db.session.rollback()
                flash(f'更新失败：{str(e)}', 'error')
                return redirect(url_for('visa_basic.visa_type_list'))

        # GET 请求处理
        if field == 'identities':
            # 从 VisaDocuments 中获取当前身份选项
            current_documents = VisaDocuments.query.filter_by(visa_type=visa_type).all()
            current_identities = [doc.singapore_identity for doc in current_documents if doc.singapore_identity != 'SHARE']
            
            # 获取所有可用的身份选项（从 VisaSingaporeIdentity 表）
            all_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
            all_identities = [identity.identity_zh for identity in all_identities]
            
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
        VisaDocuments.query.filter_by(visa_type=visa_type).delete()
        
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
