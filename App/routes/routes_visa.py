from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
import os
from datetime import datetime
from pathlib import Path
import platform
import subprocess
import shutil
import logging
from ..exts import db
from ..models import VisaCountries, VisaTypes, VisaDocuments, VisaLinks, VisaProject  # 确保从正确位置导入模型
from ..code.Visa.utils_visa import VisasUtils
import json
from flask import current_app

# 创建蓝图
visa_routes = Blueprint('visa_routes', __name__)


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


@visa_routes.route('/add_country', methods=['POST'])
def add_country():
    data = request.get_json()
    country = VisaCountries(
        country_name_CN=data['country_name_CN'],
        country_name_EN=data['country_name_EN'],
        country_code=data['country_code']
    )
    return add_to_db(country)


@visa_routes.route('/add_visa_type', methods=['POST'])
def add_visa_type():
    data = request.get_json()
    visa_type = VisaTypes(
        visa_type_name=data['visa_type_name'],
        processing_time=data['processing_time'],
        fee=data['fee'],
        country_id=data['country_id']
    )
    return add_to_db(visa_type)


@visa_routes.route('/add_document', methods=['GET', 'POST'])
def add_document():
    if request.method == 'GET':
        country = request.args.get('country', '')
        return render_template('visas/add_document.html', country=country)
        
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type = request.form.get('visa_type')
            singapore_identity = request.form.get('singapore_identity')
            document_info = request.form.get('document_info')
            additional_info = request.form.get('additional_info')

            # 数据验证
            if not all([visa_type, singapore_identity, document_info]):
                flash("所有必填字段都必须填写", "error")
                return redirect(url_for('visa_routes.add_document', country=visa_type))

            # 检查是否已存在相同签证类型和身份的记录
            existing = VisaDocuments.query.filter_by(
                visa_type=visa_type,
                singapore_identity=singapore_identity
            ).first()
            
            if existing:
                flash(f"已存在相同签证类型和身份的记录", "error")
                return redirect(url_for('visa_routes.add_document', country=visa_type))

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
            return redirect(url_for('visa_routes.manage_visas', country=visa_type))

        except Exception as e:
            db.session.rollback()
            logging.error(f"添加签证文档时发生错误: {str(e)}")
            flash(f"添加失败: {str(e)}", "error")
            return redirect(url_for('visa_routes.add_document', country=visa_type))

    return render_template('visas/add_document.html')


@visa_routes.route('/visa_processing/<country>', methods=['GET', 'POST'])
def visa_processing(country):
    # 获取并解析form_data
    form_data_str = request.args.get('form_data', '{}')
    try:
        form_data = json.loads(form_data_str)
    except:
        form_data = {}
    
    # 如果没有singapore_status，设置默认值为'PR'
    if 'singapore_status' not in form_data:
        form_data['singapore_status'] = 'PR'

    # 获取签证类型信息
    types_info = VisaTypes.query.filter_by(visa_type_name=country).first()
    
    # 获取相关链接
    links = VisaLinks.query.filter_by(visa_type=country).order_by(VisaLinks.name.asc()).all()

    # 获取签证文档数据
    documents = VisaDocuments.query.filter_by(visa_type=country).all()
    document_data = {}
    
    # 获取共用资料
    common_doc = VisaDocuments.query.filter_by(
        visa_type=country,
        singapore_identity='SHARE'
    ).first()

    # 处理每个身份的文档数据
    for doc in documents:
        if doc.singapore_identity == 'SHARE':
            continue  # 跳过共用资料的单独处理
            
        document_info = []
        additional_info = []

        # 添加共用资料（如果存在）
        if common_doc and common_doc.document_info:
            document_info.append(common_doc.document_info)
        if common_doc and common_doc.additional_info:
            additional_info.append(common_doc.additional_info)

        # 添加特定身份资料
        if doc.document_info:
            if document_info:  # 如果已有共用资料，添加换行符
                document_info.append("\n")
            document_info.append(doc.document_info)
        if doc.additional_info:
            if additional_info:  # 如果已有共用资料的补充信息，添加换行符
                additional_info.append("\n")
            additional_info.append(doc.additional_info)

        # 保存处理后的数据
        document_data[doc.singapore_identity] = {
            'document_info': "\n".join(document_info) if document_info else "暂无文件资料",
            'additional_info': "\n".join(additional_info) if additional_info else "暂无补充信息"
        }

    # 单独处理共用资料显示
    if common_doc:
        document_data['SHARE'] = {
            'document_info': common_doc.document_info if common_doc.document_info else "暂无文件资料",
            'additional_info': common_doc.additional_info if common_doc.additional_info else "暂无补充信息"
        }

    # 获取项目列表
    project_root = Path(__file__).resolve().parent.parent
    project_path = project_root / "static" / "资源" / "Project" / "Visa"
    project_list = [folder for folder in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, folder))]
    projects = [item for item in project_list if country in item]

    return render_template('visas/签证项目页面.html',
                         form_data=form_data,
                         country=country,
                         types_info=types_info,
                         links=links,
                         projects=projects,
                         document_data=document_data)


@visa_routes.route('/visa/<country>/open_project_folder', methods=['GET', 'POST'])
def visa_open_project_folder(country):
    # 打开对应国家的签证资源文件夹
    current_dir = Path.cwd()

    folder_path = current_dir / "App" / "static" / "资源" / "签证" / country

    if not folder_path.exists():
        flash(f"资源文件夹 {folder_path} 不存在", "error")
        return redirect(url_for("visa_routes.visa_processing", country=country))

    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other Unix-based systems
            subprocess.run(["xdg-open", folder_path])
    except Exception as e:
        flash(f"无法打开文件夹: {str(e)}", "error")

    return redirect(url_for("visa_routes.visa_processing", country=country))


@visa_routes.route('/visa/<file_name>/<country>/visa_open_current_project', methods=['GET', 'POST'])
def visa_open_current_project(file_name, country):
    # 根目录（可以放到配置文件或环境变量中）
    # 创建文件夹路径
    project_root = Path(__file__).resolve().parent.parent  # 获取项目的根目录路径
    base_folder = project_root / "static" / "资源" / "Project" / "Visa"

    # 拼接目标路径
    folder_path = base_folder / file_name
    if not folder_path.exists():
        flash(f"资源文件夹 {folder_path} 不存在", "error")
        return redirect(url_for("visa_routes.visa_processing", country=country))

    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other Unix-based systems
            subprocess.run(["xdg-open", folder_path])

    except Exception as e:
        flash(f"无法打开文件夹: {str(e)}", "error")

    return redirect(url_for("visa_routes.visa_processing", country=country))


@visa_routes.route('/visa/<country>/visa_create_project', methods=['POST'])
def visa_create_project(country):
    try:
        project_name = request.form.get('path_create_project')
        singapore_status = request.form.get('singapore_status')
        visa_status = request.form.get('visa_status')
        estimated_date = request.form.get('estimated_date')
        submit_button = request.form.get('submit_button')

        if not all([project_name, singapore_status, visa_status, estimated_date]):
            return jsonify({
                'message': '请填写所有必填字段',
                'status': 'error'
            }), 400

        # 创建项目文件夹
        project_root = Path(__file__).resolve().parent.parent  # 获取项目的根目录路径
        project_base = project_root / "static" / "资源" / "Project" / "Visa"
        project_path = os.path.join(project_base, f"{country}_{project_name}_{singapore_status}")
        
        if not os.path.exists(project_path):
            os.makedirs(project_path)

        # 保存项目信息
        project_info = {
            'name': project_name,
            'singapore_status': singapore_status,
            'visa_status': visa_status,
            'estimated_date': estimated_date,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 将项目信息保存到数据库或文件中
        info_file = os.path.join(project_path, 'project_info.json')
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=4)

        # 复制模板文件
        source_folder = project_root / "static" / "资源" / "签证" / country
        folders_to_copy = ["共用资料", singapore_status]

        for folder in folders_to_copy:
            source_path = source_folder / folder
            if source_path.exists():
                for item in os.listdir(source_path):
                    src_item = source_path / item
                    dst_item = Path(project_path) / item
                    if src_item.is_file():
                        shutil.copy2(src_item, dst_item)
                    elif src_item.is_dir():
                        shutil.copytree(src_item, dst_item)

        # 构建重定向URL
        redirect_url = url_for('visa_routes.visa_processing', 
                             country=country,
                             form_data=json.dumps({
                                 'path_create_project': project_name,
                                 'singapore_status': singapore_status
                             }))

        return jsonify({
            'message': '项目创建成功',
            'status': 'success',
            'redirect_url': redirect_url
        })

    except Exception as e:
        logging.error(f"创建项目时发生错误: {str(e)}")
        return jsonify({
            'message': f'创建项目失败: {str(e)}',
            'status': 'error'
        }), 500


@visa_routes.route('/document_request/<country>/<singapore_status>')
def display_document_request(country, singapore_status):
    """
    从数据库中获取签证文件资料内容，并返回 JSON 格式的响应。

    参数:
    - country (str): 目标国家
    - singapore_status (str): 新加坡身份状态

    返回:
    - dict: 包含签证文件资料内容的 JSON 响应
    """
    try:
        # 获取文档信息
        document_info = VisaDocuments.get_document_info(country, singapore_status)
        
        return jsonify(document_info)
    except Exception as e:
        logging.error(f"获取签证文档时发生错误: {str(e)}")
        return jsonify({
            'document_info': '获取数据时发生错误',
            'additional_info': '获取数据时发生错误'
        }), 500


@visa_routes.route('/visa/update_visa_documents')
def update_visa_documents():
    project_root = Path(__file__).resolve().parent.parent  # 获取项目的根目录路径
    directory_path = project_root / "static" / "资源" / "签证"
    identity_path = directory_path / "Z-模板"

    # 检查主目录是否存在
    if not directory_path.exists():
        print("目录不存在")
        return jsonify({"message": "签证资源目录不存在"}), 404

    # 获取所有签证类型和身份模板文件夹名称
    folder_names = [f.name for f in directory_path.iterdir() if f.is_dir() and f.name != "Z-模板"]
    identitys = [f.name for f in identity_path.iterdir() if f.is_dir()]
    identitys.remove("共用资料")
    # 处理签证类型和身份模板数据
    visa_info = {}

    for visa_type in folder_names:
        visa_info[visa_type] = identitys
        # 打印身份模板名称
        for singapore_identity in identitys:
            print(singapore_identity)
            existing_document = VisaDocuments.query.filter_by(visa_type=visa_type,
                                                              singapore_identity=singapore_identity).first()

            # 如果记录不存在则插入
            if not existing_document:
                document_info = "待输入"
                additional_info = "待输入"
                VisaDocuments.insert_data(visa_type, singapore_identity, document_info, additional_info)

            else:
                print(f"记录已存在，跳过插入：签证类型 - {visa_type}, 新加坡身份 - {singapore_identity}")

    # 重定向到主页并输出签证类型和模板
    return redirect(url_for("index.index"))


@visa_routes.route('/visa/manage_visas')
def manage_visas():
    country = request.args.get('country', '')
    visa_type = request.args.get('visa_type', '')

    # 查询所有签证类型列表供选择框使用
    visa_types = [type.visa_type_name for type in VisaTypes.query.order_by(VisaTypes.visa_type_name).all()]

    # 根据国家和签证类型过滤文档数据
    query = VisaDocuments.query
    if country:
        query = query.filter_by(visa_type=country)
    if visa_type:
        query = query.filter_by(visa_type=visa_type)
    
    documents = query.all()

    return render_template('visas/visa_documents.html', 
                         documents=documents, 
                         visa_types=visa_types,
                         current_country=country)


@visa_routes.route('/visa/edit/<int:id>', methods=['GET'])
def edit_visa(id):
    document = VisaDocuments.query.get_or_404(id)
    return render_template('visas/edit_visa_document.html', document=document)


@visa_routes.route('/visa/update/<int:id>', methods=['GET', 'POST'])
def update_visa(id):
    document = VisaDocuments.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            visa_type = request.form.get('visa_type')
            singapore_identity = request.form.get('singapore_identity')
            document_info = request.form.get('document_info')
            additional_info = request.form.get('additional_info')

            # 数据验证
            if not all([visa_type, singapore_identity, document_info]):
                flash("所有必填字段都必须填写", "error")
                return redirect(url_for('visa_routes.edit_visa', id=id))

            # 检查是否已存在相同签证类型和身份的记录（排除当前记录）
            existing = VisaDocuments.query.filter(
                VisaDocuments.visa_type == visa_type,
                VisaDocuments.singapore_identity == singapore_identity,
                VisaDocuments.id != id
            ).first()
            
            if existing:
                flash(f"已存在相同签证类型和身份的记录", "error")
                return redirect(url_for('visa_routes.edit_visa', id=id))

            # 更新记录
            document.visa_type = visa_type
            document.singapore_identity = singapore_identity
            document.document_info = document_info
            document.additional_info = additional_info

            db.session.commit()
            flash("签证记录已更新", "success")
            return redirect(url_for('visa_routes.manage_visas', country=visa_type))

        except Exception as e:
            db.session.rollback()
            logging.error(f"更新签证文档时发生错误: {str(e)}")
            flash(f"更新失败: {str(e)}", "error")
            return redirect(url_for('visa_routes.edit_visa', id=id))

    return render_template('visas/edit_visa_document.html', document=document)


# 获取项目文件夹及其创建日期
def get_project_folders_with_dates(projects_dir, excluded_folders):
    project_info = []
    for folder in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder)
        if os.path.isdir(folder_path) and folder not in excluded_folders:
            created_time = os.path.getctime(folder_path)
            created_date = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d')
            project_info.append({'name': folder, 'created_date': created_date})
    return project_info


@visa_routes.route('/visa/show_current_all_projects', methods=['GET'])
def show_current_all_projects():
    # 获取排序参数，默认按项目名称排序
    sort_by = request.args.get('sort_by', 'name')
    visa_status = request.args.get('visa_status', 'pending_submission')  # 默认显示待递交

    # 基础查询
    query = VisaProject.query

    # 根据签证状态筛选
    if visa_status == 'pending_submission':
        query = query.filter_by(visa_status='待递交')
    elif visa_status == 'submitted':
        query = query.filter_by(visa_status='待出签')
    elif visa_status == 'approved':
        query = query.filter_by(visa_status='已出签')

    # 排除特定签证类型的项目（如有需求）
    visa_type_names = VisaTypes.query.with_entities(VisaTypes.visa_type_name).all()
    excluded_types = [name[0] for name in visa_type_names]
    if excluded_types:
        query = query.filter(~VisaProject.name.in_(excluded_types))

    # 查询项目数据
    projects = query.all()

    # 将查询结果转为字典格式
    projects = [
        {
            "id": project.id,
            "name": project.name,
            "created_date": project.created_date,
            "visa_status": project.visa_status,
            "estimated_date": project.estimated_date,
        }
        for project in projects
    ]

    # 按指定字段排序
    if sort_by == 'name':
        projects.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'created_date':
        projects.sort(key=lambda x: x['created_date'] or '', reverse=True)

    return render_template('visas/现有签证项目管理.html', projects=projects, visa_status=visa_status, sort_by=sort_by)


@visa_routes.route('/visa/open_current_project_file/<file_name>')
def open_current_project_file(file_name):
    # 创建文件夹路径
    project_root = Path(__file__).resolve().parent.parent  # 获取项目的根目录路径
    base_folder = project_root / "static" / "资源" / "Project" / "Visa"

    # 拼接目标路径
    folder_path = base_folder / file_name

    visa_status = request.args.get('visa_status', 'all')  # 默认值为 'all'
    sort_by = request.args.get('sort_by', 'name')  # 默认值为 'name'

    if not folder_path.exists():
        flash(f"资源文件夹 {folder_path} 不存在", "error")
        return redirect(url_for("visa_routes.show_current_all_projects"))

    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other Unix-based systems
            subprocess.run(["xdg-open", folder_path])

    except Exception as e:
        flash(f"无法打开文件夹: {str(e)}", "error")

    return redirect(url_for("visa_routes.show_current_all_projects", visa_status=visa_status, sort_by=sort_by))


@visa_routes.route('/visa/delete_current_project/<int:project_id>', methods=['POST'])
def delete_current_project(project_id):

    try:
        project = VisaProject.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True, "message": "项目删除成功！"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@visa_routes.route('/visa/update_project/<int:project_id>', methods=['GET', 'POST'])
def update_current_project(project_id):
    # 从数据库中获取该项目
    project = VisaProject.query.get_or_404(project_id)

    # 处理表单提交（POST）
    if request.method == 'POST':
        # 获取表单数据
        visa_status = request.form.get('visa_status')
        estimated_date = request.form.get('estimated_date')

        # 获取当前的签证状态和排序方式，用于保持页面状态
        current_visa_status = request.form.get('current_visa_status', 'all')
        current_sort_by = request.form.get('current_sort_by', 'name')

        # 更新项目的数据
        if visa_status:
            project.visa_status = visa_status

        if estimated_date:
            try:
                # 处理日期字段（如果为空或格式错误，会出现异常）
                project.estimated_date = datetime.strptime(estimated_date, '%Y-%m-%d')
            except ValueError:
                flash('日期格式错误，请使用 YYYY-MM-DD 格式。', 'error')
                return redirect(url_for('visa_routes.show_current_all_projects'))

        # 提交更改到数据库
        try:
            db.session.commit()
            flash('项目更新成功！', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

        # 重定向回项目管理页面，带上当前的签证状态和排序方式
        return redirect(
            url_for('visa_routes.show_current_all_projects', visa_status=current_visa_status, sort_by=current_sort_by))

    # 如果是 GET 请求，渲染页面并传递项目数据
    return render_template('visas/现有签证项目管理.html', project=project)


@visa_routes.route('/open_visa_folder', methods=['GET', 'POST'])
def open_visa_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "签证"
    folder_path = os.path.join(folder_path)
    os.startfile(folder_path)
    return redirect(url_for("index.index"))


""" 签证链接管理 开始 """
@visa_routes.route('/visa_link_page')
def visa_link_page():
    visa_links = VisaLinks.query.all()
    return render_template('visas/签证链接管理.html', visa_links=visa_links)

@visa_routes.route('/visa_link/add_visa_link', methods=['GET', 'POST'])
def add_visa_link():
    try:
        # 打印请求的表单数据
        visa_type = request.form.get('visa_type', '').strip()
        name = request.form.get('name', '').strip()
        link = request.form.get('link', '').strip()
        print("visa_type, name , link:", visa_type, name , link)

        if not visa_type or not name or not link:
            flash('All fields are required!', 'danger')
            return redirect(url_for('visa_routes.visa_link_page'))

        new_visa_link = VisaLinks(visa_type=visa_type, name=name, link=link)
        db.session.add(new_visa_link)
        db.session.commit()

        flash('Visa link added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('visa_routes.visa_link_page'))
@visa_routes.route('/visa_link/edit_visa_link/<int:id>', methods=['GET', 'POST'])
def edit_visa_link(id):
    visa_link = VisaLinks.query.get_or_404(id)

    if request.method == 'POST':
        visa_link.visa_type = request.form['visa_type']
        visa_link.name = request.form['name']
        visa_link.link = request.form['link']

        db.session.commit()
        flash('Visa link updated successfully!', 'success')
        return redirect(url_for('visa_routes.visa_link_page'))

    return render_template('visas/签证链接编辑.html', visa_link=visa_link)

@visa_routes.route('/visa_link/delete/<int:id>', methods=['GET'])
def delete_visa_link(id):
    visa_link = VisaLinks.query.get_or_404(id)

    db.session.delete(visa_link)
    db.session.commit()

    flash('Visa link deleted successfully!', 'success')
    return redirect(url_for('visa/visa_routes.visa_link_page'))

""" 签证链接管理 结束 """