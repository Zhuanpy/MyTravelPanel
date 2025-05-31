from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from ..exts import db
from ..models import VisaCountries, VisaTypes, VisaSingaporeIdentity
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
    return redirect(url_for('visa_routes.manage_identities'))

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
                return redirect(url_for('visa_routes.manage_countries'))

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
    visa_types = VisaTypes.query.all()
    return render_template('visas/visa_type_list.html', visa_types=visa_types)

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
                new_visa_type.identities = identities

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
            return redirect(url_for('visa_routes.visa_processing', visa_type=visa_type))

        except Exception as e:
            db.session.rollback()
            flash(f'添加失败: {str(e)}', 'error')
            return redirect(url_for('visa_routes.add_visa_type'))

    # 获取所有国家列表
    countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
    # 获取所有新加坡身份列表
    singapore_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()

    return render_template('visas/visa_type_add.html',
                           countries=countries,
                           singapore_identities=singapore_identities)

class EditVisaTypeForm(FlaskForm):
    value = StringField('值', validators=[DataRequired()])

@visa_basic.route('/visa/edit_visa_type/<visa_type>/<field>', methods=['GET', 'POST'])
def edit_visa_type(visa_type, field):
    # 获取签证类型记录
    visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first_or_404()
    form = EditVisaTypeForm()

    if request.method == 'POST':
        try:
            if field == 'identities':
                # 获取选中的身份ID列表
                selected_identity_ids = request.form.getlist('identities')
                # 获取对应的身份对象
                selected_identities = VisaSingaporeIdentity.query.filter(VisaSingaporeIdentity.id.in_(selected_identity_ids)).all()
                # 更新身份关联
                visa_type_record.identities = selected_identities
            else:
                # 获取表单数据
                new_value = request.form.get('value', '').strip()
                # 更新相应字段
                if field == 'fee':
                    visa_type_record.fee = new_value
                elif field == 'processing_time':
                    visa_type_record.processing_time = new_value

            db.session.commit()
            flash(f"{'身份' if field == 'identities' else '费用' if field == 'fee' else '处理时间'}更新成功", "success")
            return redirect(url_for('visa_basic.visa_type_list'))

        except Exception as e:
            db.session.rollback()
            flash(f"更新失败: {str(e)}", "error")
            return redirect(url_for('visa_basic.edit_visa_type', visa_type=visa_type, field=field))

    # 获取当前值
    if field == 'identities':
        current_value = visa_type_record.identities
        all_identities = VisaSingaporeIdentity.query.all()
        field_name = '新加坡身份'
        return render_template('visas/edit_visa_type.html',
                           visa_type=visa_type,
                           field=field,
                           field_name=field_name,
                           current_value=current_value,
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

""" about visa type end """
