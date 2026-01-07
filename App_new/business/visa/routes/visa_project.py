import shutil
from flask import current_app
import os
from datetime import datetime
import platform
import subprocess
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.visa.models.Visamodels import VisaTypes, VisaDocuments, VisaLinks, VisaProject, VisaCountries, VisaSingaporeIdentity, VisaProjectFile
from werkzeug.utils import secure_filename
from App_new.utils.VisaForm import VisasUtils
from App_new.utils.decorators import staff_only
import json
import traceback
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from urllib.parse import unquote

"""
项目管理 (visa_project.py):
项目列表 (/visa/project/show_current_all_projects)
项目处理 (/visa/project/visa_processing/<country>)
项目详情 (/visa/project/detail/<project_id>)

"""
# 创建蓝图
visa_project = Blueprint('visa_project', __name__, url_prefix='/visa/project')

# 定义支持表格生成的签证类型列表
SUPPORTED_FORM_GENERATION_VISA_TYPES = [
    '韩国签证',
    '韩国旅游签证', 
    '韩国商务签证',
    # 后续可以添加更多支持表格生成的签证类型
]

def is_visa_type_supported_for_form_generation(visa_type):
    """检查签证类型是否支持表格生成功能"""
    # 支持所有包含"韩国"的签证类型
    return '韩国' in visa_type

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

# 添加自定义过滤器
@visa_project.app_template_filter('status_class')
def status_class_filter(status):
    """返回状态对应的CSS类名"""
    status_classes = {
        '待递交': 'visa-status-pending',
        '待出签': 'visa-status-submitted',
        '已出签': 'visa-status-approved',
        '忽略单': 'visa-status-ignored'
    }
    return status_classes.get(status, '')

@visa_project.app_template_filter('format_date')
def format_date_filter(date):
    """格式化日期"""
    if date:
        return date.strftime('%Y-%m-%d')
    return ''

# 提供 JSON 解析过滤器，供模板中使用 value|from_json
@visa_project.app_template_filter('from_json')
def from_json_filter(value):
    try:
        if value is None or value == '':
            return {}
        if isinstance(value, dict):
            return value
        return json.loads(value)
    except Exception:
        return {}

@visa_project.route('/show_current_all_projects')
@login_required
@staff_only
def show_current_all_projects():
    """显示所有当前项目"""
    try:
        # 获取筛选参数
        visa_status = request.args.get('visa_status', '待递交')
        sort_by = request.args.get('sort_by', 'created_date')
        filter_visa_type = request.args.get('filter_visa_type', 'all')
        filter_country = request.args.get('filter_country', 'all')
        search_name = request.args.get('search_name', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20  # 每页显示20条数据

        # 构建基础查询（预加载header关系用于列表显示HID链接）
        query = VisaProject.query.options(db.joinedload(VisaProject.header))

        # 应用状态筛选
        if visa_status != 'all':
            query = query.filter(VisaProject.visa_status == visa_status)

        # 应用签证类型筛选
        if filter_visa_type != 'all':
            query = query.filter(VisaProject.visa_type == filter_visa_type)

        # 应用国家筛选
        if filter_country != 'all':
            query = query.join(VisaTypes, VisaProject.visa_type == VisaTypes.visa_type)\
                .join(VisaCountries, VisaTypes.country_id == VisaCountries.id)\
                .filter(VisaCountries.country_name_CN == filter_country)
            
        # 应用申请人姓名搜索
        if search_name:
            query = query.filter(VisaProject.applicant_name.like(f'%{search_name}%'))

        # 应用排序
        if sort_by == 'name':
            query = query.order_by(VisaProject.project_folder_name.asc())
        elif sort_by == 'status':
            query = query.order_by(VisaProject.visa_status.asc())
        else:  # 默认按创建日期排序
            query = query.order_by(VisaProject.created_date.desc())

        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        projects = pagination.items

        # 获取所有签证类型
        visa_types = VisaTypes.query.all()
        
        # 获取所有国家
        countries = VisaCountries.query.order_by(VisaCountries.country_name_CN).all()
        
        # 获取签证类型分类（用于快速链接）
        visa_categories = VisaTypes.query.distinct(VisaTypes.visa_type).all()
        
        # 获取每个项目的相关链接
        project_links = {}
        for project in projects:
            if project.visa_type:
                types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
                if types_info:
                    # 优先通过visa_type_id查找，没有数据时再通过visa_countries_id查找
                    links = VisaLinks.query.filter_by(visa_type_id=types_info.id).order_by(VisaLinks.name.asc()).all()
                    
                    # 如果通过visa_type_id没有找到链接，则通过visa_countries_id查找
                    if not links and types_info.country_id:
                        links = VisaLinks.query.filter_by(visa_countries_id=types_info.country_id).order_by(VisaLinks.name.asc()).all()
                    
                    project_links[project.id] = links

        return render_template('business/visa/签证项目管理/visa_project_list.html',
                             projects=projects,
                           pagination=pagination,
                           visa_status=visa_status,
                           sort_by=sort_by,
                           filter_visa_type=filter_visa_type,
                             filter_country=filter_country,
                             search_name=search_name,
                             visa_types=visa_types,
                             countries=countries,
                             visa_categories=visa_categories,
                             project_links=project_links)

    except Exception as e:
        flash(f'获取项目列表时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))


@visa_project.route('/visa_processing/<visa_type>', methods=['GET', 'POST'])
@login_required
@staff_only
def visa_processing(visa_type):
    """签证处理页面路由"""
    try:
        # 获取并解析form_data
        form_data_str = request.args.get('form_data', '{}')
        form_data = json.loads(form_data_str) if form_data_str else {}
        
        # 如果没有singapore_status，设置默认值为'PR'
        if 'singapore_status' not in form_data:
            form_data['singapore_status'] = 'PR'

        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not types_info:
            flash(f'签证类型 "{visa_type}" 不存在', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        # 获取相关链接 - 使用visa_type_id查询
        links = VisaLinks.query.filter_by(visa_type_id=types_info.id).order_by(VisaLinks.name.asc()).all()
        
        # 如果通过visa_type_id没有找到链接，则通过visa_countries_id查找
        if not links and types_info.country_id:
            links = VisaLinks.query.filter_by(visa_countries_id=types_info.country_id).order_by(VisaLinks.name.asc()).all()

        # 获取所有身份（使用新架构模型）
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        document_data = {}
        for identity in identities:
            info = VisaDocuments.get_document_info(types_info.id, identity.id)
            document_data[identity.identity_zh] = info
        # 处理共用资料
        share_info = VisaDocuments.get_document_info(types_info.id, None)
        document_data['SHARE'] = share_info

        # 获取项目列表
        from App_new.config import Config
        project_path = Config.VISA_PROJECTS_PATH
        
        # 添加错误处理，如果目录不存在则创建空列表
        try:
            if project_path.exists():
                project_list = [folder for folder in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, folder))]
                projects = [item for item in project_list if visa_type in item]
            else:
                projects = []
        except Exception as e:
            print(f"获取项目列表时出错: {str(e)}")
            projects = []

        return render_template('business/visa/签证项目管理/visa_project_create.html',
                             form_data=form_data,
                             visa_type=visa_type,
                             types_info=types_info,
                             links=links,
                             projects=projects,
                             document_data=document_data)
                             
    except json.JSONDecodeError:
        flash('表单数据格式错误', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))
    except Exception as e:
        flash(f'处理签证信息时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))

@visa_project.route('/delete_current_project/<int:project_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_current_project(project_id):
    try:
        # 获取项目信息
        project = VisaProject.query.get_or_404(project_id)
        project_folder_name = project.project_folder_name
        visa_type = project.visa_type

        # 构建项目文件夹路径
        from App_new.config import Config
        base_folder = Config.VISA_RESOURCES_PATH
        project_folder = base_folder / project_folder_name
        
        # 如果主路径不存在，尝试在签证类型子文件夹中查找
        if not project_folder.exists():
            project_folder = base_folder / visa_type / project_folder_name

        # 如果文件夹存在，删除文件夹
        if project_folder.exists():
            try:
                shutil.rmtree(str(project_folder))
            except Exception as e:
                error_message = f"删除文件夹失败: {str(e)}"
                print(error_message)  # 打印错误日志
                return jsonify({"success": False, "message": error_message}), 500

        # 删除数据库记录
        db.session.delete(project)
        db.session.commit()

        return jsonify({"success": True, "message": "项目删除成功！"}), 200

    except Exception as e:
        db.session.rollback()
        error_message = f"删除项目失败: {str(e)}"
        print(error_message)  # 打印错误日志
        return jsonify({"success": False, "message": error_message}), 500


@visa_project.route('/update_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def update_current_project(project_id):
    # 从数据库中获取该项目
    project = VisaProject.query.get_or_404(project_id)

    # 处理表单提交（POST）
    if request.method == 'POST':
        # 获取表单数据
        visa_status = request.form.get('visa_status')
        estimated_date = request.form.get('estimated_date')
        
        # 获取新增字段的表单数据
        visa_type = request.form.get('visa_type')
        applicant_name = request.form.get('applicant_name')
        contact_name = request.form.get('contact_name')
        remarks = request.form.get('remarks')
        hid_or_serial = request.form.get('hid_or_serial')

        # 获取当前的签证状态和排序方式，用于保持页面状态
        current_visa_status = request.form.get('current_visa_status', 'all')
        current_sort_by = request.form.get('current_sort_by', 'name')
        current_filter_visa_type = request.form.get('current_filter_visa_type', 'all')

        # 更新项目的数据
        if visa_status:
            project.visa_status = visa_status

        # 更新新增字段的数据
        if visa_type is not None:
            project.visa_type = visa_type
        if applicant_name is not None:
            project.applicant_name = applicant_name
        if contact_name is not None:
            project.contact_name = contact_name
        if remarks is not None:
            project.remarks = remarks
        if hid_or_serial is not None:
            project.hid_or_serial = hid_or_serial

        if estimated_date:
            try:
                # 处理日期字段（如果为空或格式错误，会出现异常）
                project.estimated_date = datetime.strptime(estimated_date, '%Y-%m-%d')
            except ValueError:
                flash('日期格式错误，请使用 YYYY-MM-DD 格式。', 'error')
                return redirect(url_for('visa_project.show_current_all_projects'))

        # 提交更改到数据库
        try:
            db.session.commit()
            flash('项目更新成功！', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')

        # 重定向回项目管理页面，带上当前的签证状态和排序方式
        return redirect(
            url_for('visa_project.show_current_all_projects', 
                   visa_status=current_visa_status, 
                   sort_by=current_sort_by,
                   filter_visa_type=current_filter_visa_type))

    # 如果是 GET 请求，渲染页面并传递项目数据
    return render_template('business/visa/签证项目管理/签证项目管理.html', project=project)


@visa_project.route('/edit_project/<int:project_id>', methods=['GET'])
def edit_project(project_id):
    """显示签证项目编辑页面"""
    project = VisaProject.query.get_or_404(project_id)
    return render_template('business/visa/签证项目管理/visa_project_edit.html', project=project)


@visa_project.route('/generate_form/<int:project_id>', methods=['POST'])
@csrf.exempt
def generate_form_for_project(project_id):
    """为项目生成表格"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 添加调试信息
        current_app.logger.info(f"生成表格请求 - 项目ID: {project_id}")
        current_app.logger.info(f"项目信息 - 签证类型: {project.visa_type}, HID: {project.hid_or_serial}, 申请人: {project.applicant_name}, 身份: {project.singapore_status}")
        
        # 检查签证类型是否支持表格生成
        if not is_visa_type_supported_for_form_generation(project.visa_type):
            current_app.logger.warning(f"不支持的签证类型: {project.visa_type}")
            return jsonify({
                'success': False, 
                'message': f'签证类型 "{project.visa_type}" 暂不支持表格生成功能'
            }), 400
        
        # 检查项目必要字段
        missing_fields = []
        if not project.hid_or_serial:
            missing_fields.append('HID/序列号')
        if not project.applicant_name:
            missing_fields.append('申请人姓名')
        if not project.singapore_status:
            missing_fields.append('新加坡身份')
            
        if missing_fields:
            current_app.logger.warning(f"项目信息不完整，缺少字段: {', '.join(missing_fields)}")
            return jsonify({
                'success': False, 
                'message': f'项目信息不完整，请确保以下字段已填写: {", ".join(missing_fields)}'
            }), 400
        
        # 生成表格的逻辑
        project_name = f"{project.visa_type}_{project.hid_or_serial}_{project.applicant_name}"
        visa_folder = f"{project_name}_{project.singapore_status}"
        from App_new.config import Config
        static_path = Config.PROJECT_ROOT / "App_new" / "static"
        
        # 检查项目文件夹是否存在
        visa_project_path = Config.VISA_PROJECTS_PATH
        form_path = visa_project_path / visa_folder
        
        current_app.logger.info(f"检查项目文件夹: {form_path}")
        if not form_path.exists():
            current_app.logger.warning(f"项目文件夹不存在: {form_path}")
            return jsonify({
                'success': False, 
                'message': f'项目文件夹不存在: {visa_folder}，请先创建项目'
            }), 400
        
        # 检查FormSample.xls文件是否存在
        form_sample_path = form_path / "FormSample.xls"
        current_app.logger.info(f"检查表单模板文件: {form_sample_path}")
        if not form_sample_path.exists():
            current_app.logger.warning(f"表单模板文件不存在: {form_sample_path}")
            return jsonify({
                'success': False, 
                'message': f'表单模板文件不存在: {form_sample_path}'
            }), 400
        
        # 检查韩国签证资源文件是否存在
        from App_new.config import Config
        source_path = Config.PROJECT_ROOT / "资源" / "签证" / "韩国签证" / "source"
        
        current_app.logger.info(f"检查韩国签证资源路径: {source_path}")
        
        if not source_path.exists():
            current_app.logger.warning(f"韩国签证资源文件不存在: {source_path}")
            return jsonify({
                'success': False, 
                'message': f'韩国签证资源文件不存在: {source_path}'
            }), 400
        
        # 检查坐标列表文件是否存在
        coord_file = source_path / "坐标列表.xls"
        current_app.logger.info(f"检查坐标列表文件: {coord_file}")
        if not coord_file.exists():
            current_app.logger.warning(f"坐标列表文件不存在: {coord_file}")
            return jsonify({
                'success': False, 
                'message': f'坐标列表文件不存在: {coord_file}'
            }), 400
        
        # 检查项目文件夹中的FormSample.xls文件
        project_folder = Config.VISA_PROJECTS_PATH / visa_folder
        form_sample_file = project_folder / "FormSample.xls"
        current_app.logger.info(f"检查表单模板文件: {form_sample_file}")
        if not form_sample_file.exists():
            current_app.logger.warning(f"表单模板文件不存在: {form_sample_file}")
            return jsonify({
                'success': False, 
                'message': f'表单模板文件不存在: {form_sample_file}，请确保项目文件夹中有FormSample.xls文件'
            }), 400
        
        # 根据签证类型调用相应的表格生成函数
        if '韩国' in project.visa_type:
            # 调用韩国签证表格生成函数
            from App_new.utils.VisaForm import VisasUtils
            VisasUtils.korea_visa_fill_form(visa_folder=visa_folder, static_path=str(static_path))
        else:
            return jsonify({
                'success': False, 
                'message': f'签证类型 "{project.visa_type}" 的表格生成功能尚未实现'
            }), 400
        
        return jsonify({'success': True, 'message': '表格生成成功'})
    except FileNotFoundError as e:
        current_app.logger.error(f"文件或目录不存在: {str(e)}")
        return jsonify({'success': False, 'message': f'文件或目录不存在: {str(e)}'}), 500
    except ImportError as e:
        current_app.logger.error(f"导入模块失败: {str(e)}")
        return jsonify({'success': False, 'message': f'系统配置错误，请联系管理员: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"生成表格时发生错误: {str(e)}")
        current_app.logger.error(f"错误详情: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'生成表格时发生错误: {str(e)}'}), 500


""" 签证详细 开始 """
@visa_project.route('/visa_detail/<project_name>')
@visa_project.route('/visa_detail/id/<int:project_id>')
def visa_detail(project_name=None, project_id=None):
    """签证详情页面路由"""
    try:
        print(f"DEBUG: visa_detail called with project_id={project_id}, project_name={project_name}")
        
        # 获取项目信息
        project = None
        if project_id:
            try:
                project = VisaProject.query.get_or_404(project_id)
                print(f"DEBUG: Found project with ID {project_id}: {project.project_folder_name}, visa_type={project.visa_type}")
            except Exception as e:
                print(f"DEBUG: Error getting project with ID {project_id}: {str(e)}")
                flash(f'项目不存在或已被删除', 'error')
                return redirect(url_for('visa_project.show_current_all_projects'))
        else:
            project = VisaProject.query.filter_by(project_folder_name=project_name).first()
            print(f"DEBUG: Found project with name {project_name}: {project.id if project else 'None'}")
            if not project:
                flash(f'项目不存在或已被删除', 'error')
                return redirect(url_for('visa_project.show_current_all_projects'))
        
        # 检查项目是否有签证类型
        if not project.visa_type:
            print(f"DEBUG: Project {project.id} has no visa_type")
            flash(f'项目缺少签证类型信息', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        # 获取签证类型信息
        print(f"DEBUG: Looking for visa type: {project.visa_type}")
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        if not types_info:
            print(f"DEBUG: Visa type '{project.visa_type}' not found in database")
            flash(f'签证类型 "{project.visa_type}" 不存在', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        print(f"DEBUG: Found visa type info: {types_info.visa_type}")
        
        # 获取相关链接 - 优先通过visa_type_id查找，没有数据时再通过visa_countries_id查找
        links = VisaLinks.query.filter_by(visa_type_id=types_info.id).order_by(VisaLinks.name.asc()).all()
        
        # 如果通过visa_type_id没有找到链接，则通过visa_countries_id查找
        if not links and types_info.country_id:
            print(f"DEBUG: No links found by visa_type_id, trying visa_countries_id: {types_info.country_id}")
            links = VisaLinks.query.filter_by(visa_countries_id=types_info.country_id).order_by(VisaLinks.name.asc()).all()
            print(f"DEBUG: Found {len(links)} links by visa_countries_id")
        
        print(f"DEBUG: Total links found: {len(links)}")
        
        # 获取签证文档数据 - 使用新的表结构
        documents = VisaDocuments.query.join(VisaTypes).filter(VisaTypes.visa_type == project.visa_type).all()
        document_data = {}
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 处理每个身份的文档数据
        for doc in documents:
            if doc.singapore_identity_id is None:
                continue  # 跳过singapore_identity_id为None的记录
            
            # 检查singapore_identity是否为None
            if doc.singapore_identity is None:
                print(f"警告: 文档ID {doc.id} 的singapore_identity为None，跳过处理")
                continue
            
            # 使用新的get_document_info方法获取文档信息
            doc_info = VisaDocuments.get_document_info(types_info.id, doc.singapore_identity_id)
            
            # 保存处理后的数据
            document_data[doc.singapore_identity.identity_zh] = {
                'document_info': doc_info['document_info'],
                'additional_info': doc_info['additional_info']
            }
        
        # 单独处理SHARE共用资料显示
        if share_identity_id:
            share_doc_info = VisaDocuments.get_document_info(types_info.id, share_identity_id)
            document_data['SHARE'] = {
                'document_info': share_doc_info['document_info'],
                'additional_info': share_doc_info['additional_info']
            }
        
        # 获取项目的资料准备状态
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        project_document_statuses = VisaProjectDocumentStatus.query.filter_by(
            project_id=project.id
        ).all()
        
        # 将资料状态转换为字典格式，方便模板使用
        document_statuses = {}
        for status in project_document_statuses:
            document_statuses[status.document_name] = {
                'id': status.id,
                'is_ready': status.is_ready,
                'notes': status.notes,
                'document_type': status.document_type
            }
        
        print(f"DEBUG: Rendering template with project={project.id}, document_data keys={list(document_data.keys())}")
        print(f"DEBUG: Project document statuses count: {len(project_document_statuses)}")
        
        # 检查项目是否已关联HID和REF
        has_header = project.header_id is not None
        has_ref = project.ref_id is not None
        
        return render_template('business/visa/签证项目管理/visa_project_detail.html',
                             project=project,
                             types_info=types_info,
                             links=links,
                             document_data=document_data,
                             document_statuses=document_statuses,
                             has_header=has_header,
                             has_ref=has_ref)
                             
    except Exception as e:
        print(f"DEBUG: Exception in visa_detail: {str(e)}")
        print(f"DEBUG: Exception traceback: {traceback.format_exc()}")
        flash(f'获取签证详情时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))


@visa_project.route('/create_project_links/<int:project_id>', methods=['POST'])
@csrf.exempt
def create_project_links(project_id):
    """为签证项目创建HID和REF关联"""
    try:
        from App_new.business.projects.models.project import ProjectHeader
        from App_new.business.projects.models.ref import ProjectRef
        from App_new.shared.models.business_types import BusinessType
        from App_new.auth.models.auth import AuthUser, UserProfile
        
        # 获取签证项目
        project = VisaProject.query.get_or_404(project_id)
        
        # 检查是否已经有关联
        if project.header_id and project.ref_id:
            return jsonify({
                'success': False,
                'message': '项目已关联HID和REF'
            }), 400
        
        # 获取签证业务类型ID
        visa_business_type = BusinessType.query.filter_by(code='visa').first()
        if not visa_business_type:
            return jsonify({
                'success': False,
                'message': '未找到签证业务类型'
            }), 400
        
        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        
        # 自动获取当前登录员工的姓名
        staff_name = ''
        leader_name = ''
        
        if current_user:
            # 获取员工档案信息
            profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            if profile:
                staff_name = profile.get_full_name()
                leader_name = profile.get_full_name()  # 经办人和负责人都使用同一个员工姓名
            else:
                staff_name = current_user.username
                leader_name = current_user.username
        
        # 如果没有获取到员工信息，使用申请人姓名作为备选
        if not staff_name:
            staff_name = project.applicant_name or '未知员工'
            leader_name = project.applicant_name or '未知员工'
        
        # 创建或获取项目主表（HID）
        header = None
        if not project.header_id:
            # 生成HID
            hid = ProjectHeader.generate_hid()
            
            # 创建项目主表
            header = ProjectHeader(
                hid=hid,
                desc=f"{project.applicant_name} {project.visa_type}签证项目",
                company_id=None,  # 设置为NULL，表示个人客户
                contact=project.contact_name or project.applicant_name,
                staff_name=staff_name or project.applicant_name,  # 使用选择的员工姓名作为经办人姓名
                leader_name=leader_name or staff_name or project.applicant_name,  # 使用选择的员工姓名作为负责人姓名
                currency='SGD',
                type='visa',
                status='active'
            )
            db.session.add(header)
            db.session.flush()  # 获取header.id
            
            # 更新签证项目的header_id和hid_or_serial
            project.header_id = header.id
            project.hid_or_serial = hid  # 自动填充HID到hid_or_serial字段
            print(f"DEBUG: Created header with ID {header.id}, HID: {hid}")
            
            # 自动添加申请人到人员名单
            from App_new.business.projects.models.project_member import ProjectMember
            member = ProjectMember(
                header_id=header.id,
                title='',  # 默认无称谓
                member_name=project.applicant_name,
                member_name_en='',
                member_role='申请人',
                member_phone=project.contact_phone if hasattr(project, 'contact_phone') else '',
                member_email=project.contact_email if hasattr(project, 'contact_email') else '',
                is_leader=True,  # 设为Leader
                remarks=f'从签证项目自动创建'
            )
            db.session.add(member)
            db.session.flush()
            print(f"DEBUG: Created member with ID {member.id}, name: {project.applicant_name}")
        
        # 创建REF明细
        ref = None
        if not project.ref_id:
            # 生成REF编号
            ref_number = ProjectRef.generate_ref_number(header.hid if header else None)
            
            # 准备签证相关的额外信息（与签证REF页面结构兼容）
            country_name = types_info.country.country_name_CN if types_info and types_info.country else '未知'
            country_name_en = types_info.country.country_name_EN if types_info and types_info.country else ''
            country_code = types_info.country.country_code if types_info and types_info.country else ''

            # 将国家转换为 create_visa_ref.html 期望的代码格式
            country_code_map = {
                'CN': 'CHINA', 'CHN': 'CHINA', 'CHINA': 'CHINA',
                'IN': 'INDIA', 'IND': 'INDIA', 'INDIA': 'INDIA',
                'VN': 'VIETNAM', 'VNM': 'VIETNAM', 'VIETNAM': 'VIETNAM',
                'TH': 'THAILAND', 'THA': 'THAILAND', 'THAILAND': 'THAILAND',
                'JP': 'JAPAN', 'JPN': 'JAPAN', 'JAPAN': 'JAPAN',
                'KR': 'KOREA', 'KOR': 'KOREA', 'KOREA': 'KOREA',
                'AU': 'AUSTRALIA', 'AUS': 'AUSTRALIA', 'AUSTRALIA': 'AUSTRALIA',
                'US': 'USA', 'USA': 'USA', 'UNITED STATES': 'USA',
                'GB': 'UK', 'GBR': 'UK', 'UK': 'UK', 'UNITED KINGDOM': 'UK',
                'MY': 'MALAYSIA', 'MYS': 'MALAYSIA', 'MALAYSIA': 'MALAYSIA',
                'ID': 'INDONESIA', 'IDN': 'INDONESIA', 'INDONESIA': 'INDONESIA',
                'PH': 'PHILIPPINES', 'PHL': 'PHILIPPINES', 'PHILIPPINES': 'PHILIPPINES',
            }
            # 优先使用 country_code，其次使用英文名
            country_for_ref = country_code_map.get(country_code.upper(),
                             country_code_map.get(country_name_en.upper(), 'OTHER')) if country_code or country_name_en else 'OTHER'

            # 将签证类型转换为 create_visa_ref.html 期望的代码格式
            visa_type_map = {
                '旅游签证': 'TOURIST', '旅游': 'TOURIST', 'TOURIST': 'TOURIST',
                '商务签证': 'BUSINESS', '商务': 'BUSINESS', 'BUSINESS': 'BUSINESS',
                '工作签证': 'WORK', '工作': 'WORK', 'WORK': 'WORK',
                '学生签证': 'STUDENT', '留学签证': 'STUDENT', '学生': 'STUDENT', 'STUDENT': 'STUDENT',
                '过境签证': 'TRANSIT', '过境': 'TRANSIT', 'TRANSIT': 'TRANSIT',
                '多次入境': 'MULTIPLE', '多次签证': 'MULTIPLE', 'MULTIPLE': 'MULTIPLE',
            }
            visa_type_for_ref = visa_type_map.get(project.visa_type, 'TOURIST') if project.visa_type else 'TOURIST'

            # 生成中文和英文版的签证名称
            visa_name = f"{country_name} {project.visa_type}"  # 中文版保留兼容
            visa_name_en = f"{country_for_ref} {visa_type_for_ref} VISA"  # 英文版用于 description
            
            # 解析申请费用，提取数字部分
            selling_price = 0
            if types_info and types_info.fee:
                try:
                    # 尝试从费用字符串中提取数字
                    import re
                    fee_match = re.search(r'(\d+(?:\.\d+)?)', types_info.fee)
                    if fee_match:
                        selling_price = float(fee_match.group(1))
                        print(f"DEBUG: Extracted selling price: {selling_price} from fee: {types_info.fee}")
                except (ValueError, AttributeError) as e:
                    print(f"DEBUG: Failed to extract selling price from fee '{types_info.fee}': {str(e)}")
            
            # 获取人员信息
            from App_new.business.projects.models.project_member import ProjectMember
            member_id = None
            pax_names_list = []
            
            # 查询项目的所有人员
            header_id_to_use = header.id if header else project.header_id
            existing_members = ProjectMember.query.filter_by(header_id=header_id_to_use).all()
            if existing_members:
                pax_names_list = [m.id for m in existing_members]
                # 找到Leader或第一个人员
                leader_member = next((m for m in existing_members if m.is_leader), existing_members[0] if existing_members else None)
                member_id = leader_member.id if leader_member else None
            
            visa_extra_info = {
                # 新版签证REF页面字段（使用转换后的英文代码）
                'visa_name': visa_name,
                'country': country_for_ref,  # 使用英文代码: CHINA, INDIA 等
                'visa_type': visa_type_for_ref,  # 使用英文代码: TOURIST, BUSINESS 等
                'processing_type': 'NORMAL',  # 默认普通处理
                'pax_names': pax_names_list,
                'leader_id': member_id,
                'departure_date': '',
                'pax_names_display': project.applicant_name,
                # Pricing 信息（默认1个成人，使用提取的费用）
                'adult_qty': 1,
                'adult_selling': selling_price,
                'adult_cost': 0,
                'child_qty': 0,
                'child_selling': 0,
                'child_cost': 0,
                'infant_qty': 0,
                'infant_selling': 0,
                'infant_cost': 0,
                # 原有签证项目字段（保留兼容性）
                'visa_country': country_name,
                'visa_country_code': types_info.country.country_code if types_info and types_info.country else None,
                'singapore_status': project.singapore_status,
                'visa_status': project.visa_status,
                'processing_time': types_info.processing_time if types_info else None,
                'visa_fee': types_info.fee if types_info else None,
                'source_system': 'visa_system',
                'created_from_visa_project': True,
                'visa_project_id': project.id,
                'contact_name': project.contact_name or project.applicant_name,
                'contact_phone': project.contact_phone if hasattr(project, 'contact_phone') else None,
                'contact_email': project.contact_email if hasattr(project, 'contact_email') else None,
                'leader_name': project.applicant_name
            }
            
            # 创建REF明细
            ref = ProjectRef(
                header_id=header.id if header else project.header_id,
                ref_number=ref_number,
                description=visa_name_en,  # 使用英文格式: CHINA TOURIST VISA
                ref_type_id=visa_business_type.id,
                detailed_description=visa_name_en,  # 使用英文格式
                selling_price=selling_price,  # 使用申请费用作为售价
                cost_price=0,
                currency='SGD',
                remarks=project.remarks,
                status='processing',
                payment_status='unpaid',
                extra_info=json.dumps(visa_extra_info, ensure_ascii=False)
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id
            
            # 更新签证项目的ref_id
            project.ref_id = ref.id
            print(f"DEBUG: Created ref with ID {ref.id}, REF: {ref_number}")
        
        # 提交事务
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'HID和REF创建成功',
            'header_id': header.id if header else project.header_id,
            'ref_id': ref.id if ref else project.ref_id,
            'hid': header.hid if header else None,
            'ref_number': ref.ref_number if ref else None
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error creating project links: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建HID和REF时出错：{str(e)}'
        }), 500


@visa_project.route('/update_visa_status', methods=['POST'])
@csrf.exempt
def update_visa_status():
    """更新项目状态"""
    try:
        # 获取并验证参数
        project_id = request.form.get('project_id')
        new_status = request.form.get('status')
        
        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少项目ID'
            }), 400
            
        if not new_status:
            return jsonify({
                'success': False,
                'message': '缺少状态值'
            }), 400
            
        # 验证状态值是否有效
        valid_statuses = ['待递交', '待出签', '已出签', '忽略单']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'无效的状态值。必须是以下值之一：{", ".join(valid_statuses)}'
            }), 400
            
        # 获取项目
        project = VisaProject.query.get_or_404(project_id)
            
        # 更新状态
        project.visa_status = new_status
        
        # 如果状态是"已出签"，更新出签日期
        if new_status == '已出签':
            project.visa_approved_date = datetime.now()
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'项目状态已更新为：{new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新签证状态时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'更新状态时出错：{str(e)}'
        }), 500


@visa_project.route('/<visa_type>/visa_create_project', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def visa_create_project(visa_type):
    try:
        # 获取表单数据
        hid_or_serial = request.form.get('hid_or_serial')
        applicant_name = request.form.get('applicant_name')
        visa_type_input = request.form.get('visa_type')
        singapore_status = request.form.get('singapore_status')
        visa_status = request.form.get('visa_status')
        estimated_date = request.form.get('estimated_date')
        submit_button = request.form.get('submit_button')
        
        # 获取资料状态数据
        document_statuses_json = request.form.get('document_statuses', '[]')
        try:
            document_statuses = json.loads(document_statuses_json)
            print(f"DEBUG: Received document_statuses: {document_statuses}")
        except json.JSONDecodeError:
            document_statuses = []
            print("DEBUG: Failed to parse document_statuses JSON")

        # 验证必填字段（hid_or_serial为可选，可后续通过创建HID自动填充）
        if not applicant_name or not visa_type_input or not singapore_status or not visa_status or not estimated_date:
            error_msg = "缺少必要的项目信息，请确保所有必填字段已填写"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            flash(error_msg, 'error')
            return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

        # 自动生成项目名称（hid_or_serial可能为空）
        hid_part = hid_or_serial if hid_or_serial else 'NEW'
        project_name = f"{visa_type_input}_{hid_part}_{applicant_name}"

        # 如果是生成表格，直接重定向到处理页面
        if submit_button == 'generate_form':
            try:
                visa_folder = f"{project_name}_{singapore_status}"
                from App_new.config import Config
                static_path = Config.PROJECT_ROOT / "App" / "static"
                VisasUtils.korea_visa_fill_form(visa_folder=visa_folder, static_path=str(static_path))

                # 如果是 AJAX 请求，返回 JSON 响应
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': '表格生成成功',
                        'redirect_url': url_for('visa_project.visa_processing', visa_type=visa_type)
                    })
                # 否则直接重定向
                return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

            except FileNotFoundError as e:
                error_msg = f"文件或目录不存在: {str(e)}"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 500
                flash(error_msg, 'error')
                return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

            except Exception as e:
                error_msg = f"生成表格时发生错误: {str(e)}"
                print(error_msg)  # 调试日志
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 500
                flash(error_msg, 'error')
                return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

        """ 创建项目思路 """
        "a 创建项目文件夹"
        from App_new.config import Config
        visa_folder = Config.VISA_PROJECTS_PATH  # 签证项目文件夹
        project_file_name = f"{project_name}_{singapore_status}"
        project_folder = visa_folder / project_file_name
        os.makedirs(project_folder, exist_ok=True)

        "b 将资源文件夹内容复制到创建项目文件夹"
        source_path = Config.VISA_RESOURCES_PATH / visa_type  # 签证资源文件，储存表格及表格坐标
        share_path = source_path / '共用资料'  # 共用资料文件夹复制到指定文件夹
        id_path = source_path / singapore_status  # 身份文件夹资料 复制到 指定文件夹

        folders = [share_path, id_path]

        for file_path in folders:
            # 检查路径是否存在，如果不存在则创建
            if not file_path.exists():
                print(f"Creating directory: {file_path}")
                file_path.mkdir(parents=True, exist_ok=True)

            # 复制源文件夹中的文件
            for file in file_path.iterdir():
                if file.is_file():
                    dst_path = project_folder / file.name
                    shutil.copy2(file, dst_path)
                    print(f"Copied file: {file} -> {dst_path}")

        # 保存到数据库
        new_project = VisaProject(
            name=project_file_name,
            visa_status=visa_status,
            estimated_date=datetime.strptime(estimated_date, '%Y-%m-%d').date()
        )

        # 添加新字段数据
        new_project.project_folder_name = project_file_name
        new_project.visa_type = visa_type_input
        new_project.applicant_name = applicant_name
        new_project.contact_name = request.form.get('contact_name')
        new_project.remarks = request.form.get('remarks')
        new_project.hid_or_serial = hid_or_serial if hid_or_serial else None  # 可为空
        new_project.singapore_status = singapore_status

        db.session.add(new_project)
        db.session.flush()  # 获取项目ID
        
        # 保存资料状态数据
        if document_statuses:
            from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
            print(f"DEBUG: Saving {len(document_statuses)} document statuses")
            for status_data in document_statuses:
                is_ready = status_data['is_ready']
                print(f"DEBUG: Saving document {status_data['document_name']} with is_ready={is_ready} (type: {type(is_ready)})")
                # 确保is_ready是布尔值
                if isinstance(is_ready, str):
                    is_ready = is_ready.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(is_ready, int):
                    is_ready = bool(is_ready)
                elif not isinstance(is_ready, bool):
                    is_ready = False
                
                print(f"DEBUG: Final is_ready value: {is_ready} (type: {type(is_ready)})")
                
                new_status = VisaProjectDocumentStatus(
                    project_id=new_project.id,
                    document_name=status_data['document_name'],
                    document_type=status_data['document_type'],
                    is_ready=is_ready,
                    notes=status_data.get('notes', '')
                )
                db.session.add(new_status)
        else:
            print("DEBUG: No document statuses to save")
        
        db.session.commit()

        # 如果是 AJAX 请求，返回 JSON 响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': f'项目创建成功: {project_file_name}',
                'redirect_url': url_for('visa_project.visa_detail', project_id=new_project.id)
            })

        # 否则重定向到项目详情页面
        flash(f'项目创建成功: {project_file_name}', 'success')
        return redirect(url_for('visa_project.visa_detail', project_id=new_project.id))

    except Exception as e:
        error_msg = f"创建项目失败: {str(e)}"
        print(error_msg)  # 调试日志
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
        flash(error_msg, 'error')
        return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

@visa_project.route('/update_project_details/<int:project_id>', methods=['POST'])
@csrf.exempt
def update_project_details(project_id):
    """处理签证项目编辑表单提交"""
    try:
        project = VisaProject.query.get_or_404(project_id)

        # 获取表单数据
        hid_or_serial = request.form.get('hid_or_serial')
        visa_type = request.form.get('visa_type')
        applicant_name = request.form.get('applicant_name')
        contact_name = request.form.get('contact_name')
        visa_status = request.form.get('visa_status')
        singapore_status = request.form.get('singapore_status')
        estimated_date = request.form.get('estimated_date')
        remarks = request.form.get('remarks')

        # 验证必填字段（hid_or_serial为可选，可后续通过创建HID自动填充）
        if not all([visa_type, applicant_name, visa_status, singapore_status, estimated_date]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': '缺少必要的项目信息，请确保所有必填字段已填写'
                }), 400
            flash('缺少必要的项目信息，请确保所有必填字段已填写', 'error')
            return redirect(url_for('visa_project.edit_project', project_id=project_id))

        # 更新项目数据（hid_or_serial可为空）
        project.hid_or_serial = hid_or_serial if hid_or_serial else None
        project.visa_type = visa_type
        project.applicant_name = applicant_name
        project.contact_name = contact_name
        project.visa_status = visa_status
        project.singapore_status = singapore_status
        project.remarks = remarks

        # 处理日期字段
        try:
            project.estimated_date = datetime.strptime(estimated_date, '%Y-%m-%d').date()
        except ValueError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': '日期格式错误，请使用YYYY-MM-DD格式'
                }), 400
            flash('日期格式错误，请使用YYYY-MM-DD格式', 'error')
            return redirect(url_for('visa_project.edit_project', project_id=project_id))

        # 保存到数据库
        db.session.commit()

        # 返回成功响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': '项目更新成功',
                'redirect_url': url_for('visa_project.show_current_all_projects')
            })

        flash('项目更新成功', 'success')
        return redirect(url_for('visa_project.show_current_all_projects'))

    except Exception as e:
        db.session.rollback()
        error_msg = f"更新项目失败: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
        flash(error_msg, 'error')
        return redirect(url_for('visa_project.edit_project', project_id=project_id))


@visa_project.route('/update_estimated_date/<int:project_id>', methods=['POST'])
@csrf.exempt
def update_estimated_date(project_id):
    """通过AJAX更新预估出签日期"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 获取日期数据
        estimated_date = request.form.get('estimated_date')
        
        if not estimated_date:
            return jsonify({
                'success': False,
                'message': '预估出签日期不能为空'
            }), 400
        
        # 处理日期字段
        try:
            project.estimated_date = datetime.strptime(estimated_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': '日期格式错误，请使用YYYY-MM-DD格式'
            }), 400
        
        # 保存到数据库
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '预估出签日期更新成功',
            'estimated_date': estimated_date
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"更新预估出签日期失败: {str(e)}"
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500


@visa_project.route('/open_folder', methods=['GET'])
def open_folder():
    """
    通用文件夹打开函数，替代多个类似功能的路由

    参数：
    - folder_type: 文件夹类型，可选值：project(项目文件夹)、visa_type(签证类型文件夹)、visa_root(签证根目录)
    - project_folder: 项目文件夹名称，用于folder_type=project
    - visa_type: 签证类型，用于folder_type=visa_type
    """
    try:
        # 获取并解码参数
        folder_type = request.args.get('folder_type', 'project')
        project_folder = unquote(request.args.get('project_folder', ''))
        visa_type = unquote(request.args.get('visa_type', ''))

        print(f"DEBUG: folder_type={folder_type}, project_folder='{project_folder}', visa_type='{visa_type}'")

        # 获取项目根目录
        from App_new.config import Config

        # 根据文件夹类型构建路径
        if folder_type == 'project' and project_folder and visa_type:
            base_folder = Config.VISA_PROJECTS_PATH
            # 首先尝试在签证类型子文件夹中查找
            folder_path = base_folder / visa_type / project_folder
            if not folder_path.exists():
                # 如果不存在，尝试在根目录中查找
                folder_path = base_folder / project_folder

            print(f"DEBUG: 尝试路径1: {folder_path}")

            if not folder_path.exists():
                # 文件夹不存在时自动创建
                try:
                    # 优先在签证类型子文件夹中创建
                    folder_path = base_folder / visa_type / project_folder
                    folder_path.mkdir(parents=True, exist_ok=True)
                    print(f"DEBUG: 自动创建文件夹: {folder_path}")
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "message": f"创建文件夹失败：{str(e)}"
                    }), 500

        elif folder_type == 'visa_type' and visa_type:
            # 修改为正确的签证类型资源文件夹路径
            folder_path = Config.VISA_RESOURCES_PATH / visa_type
            if not folder_path.exists():
                return jsonify({
                    "success": False, 
                    "message": f"找不到签证类型文件夹：{visa_type}"
                }), 404

            print(f"DEBUG: 尝试路径2: {folder_path}")

        elif folder_type == 'visa_root':
            # 修改为正确的签证根目录路径
            folder_path = Config.VISA_RESOURCES_PATH
            if not folder_path.exists():
                return jsonify({
                    "success": False, 
                    "message": "找不到签证根目录"
                }), 404

            print(f"DEBUG: visa_root 路径: {folder_path}")

        else:
            return jsonify({
                "success": False, 
                "message": "无效的文件夹类型或参数缺失"
            }), 400

        print(f"DEBUG: 最终打开路径: {folder_path}")

        # 打开文件夹
        if platform.system() == 'Windows':
            # 使用 explorer 命令确保文件夹置顶显示
            subprocess.run(['explorer', str(folder_path)], shell=True)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', str(folder_path)])
        else:  # Linux
            subprocess.run(['xdg-open', str(folder_path)])

        return jsonify({
            "success": True, 
            "message": "文件夹已打开"
        })

    except Exception as e:
        current_app.logger.error(f"打开文件夹时发生错误: {str(e)}")
        return jsonify({
            "success": False, 
            "message": f"打开文件夹时发生错误：{str(e)}"
        }), 500

@visa_project.route('/delete_project/<int:project_id>', methods=['POST'])
@csrf.exempt
def delete_project(project_id):
    """删除签证项目"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 删除项目文件夹
        from App_new.config import Config
        project_folder = Config.VISA_PROJECTS_PATH / project.project_folder_name
        if project_folder.exists():
            shutil.rmtree(project_folder)
        
        # 从数据库中删除项目
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '项目已成功删除'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除项目时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除项目时出错：{str(e)}'
        }), 500

@visa_project.route('/save_document_status', methods=['POST'])
@csrf.exempt
def save_document_status():
    """保存项目资料准备状态"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        document_statuses = data.get('document_statuses', [])
        
        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少项目ID'
            }), 400
        
        # 获取项目
        project = VisaProject.query.get_or_404(project_id)
        
        # 删除现有的资料状态记录
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        VisaProjectDocumentStatus.query.filter_by(project_id=project_id).delete()
        
        # 创建新的资料状态记录
        for status_data in document_statuses:
            new_status = VisaProjectDocumentStatus(
                project_id=project_id,
                document_name=status_data['document_name'],
                document_type=status_data['document_type'],
                is_ready=status_data['is_ready'],
                notes=status_data.get('notes', '')
            )
            db.session.add(new_status)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '资料准备状态已保存'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"保存资料准备状态时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }), 500


@visa_project.route('/get_document_status/<int:project_id>')
def get_document_status(project_id):
    """获取项目资料准备状态"""
    try:
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        
        # 获取项目的资料准备状态
        statuses = VisaProjectDocumentStatus.query.filter_by(project_id=project_id).all()
        
        # 转换为字典格式
        status_list = [status.to_dict() for status in statuses]
        
        return jsonify({
            'success': True,
            'document_statuses': status_list
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资料准备状态时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败：{str(e)}'
        }), 500


@visa_project.route('/get_project_documents/<visa_type>/<identity>')
def get_project_documents(visa_type, identity):
    """获取指定签证类型和身份的所需资料列表（包含共用资料+特定身份资料）"""
    try:
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
        
        # URL解码
        from urllib.parse import unquote
        import html
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        decoded_identity = unquote(identity)
        decoded_identity = html.unescape(decoded_identity)
        
        print(f"DEBUG: 获取项目资料 - 签证类型: {decoded_visa_type}, 身份: {decoded_identity}")
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 404
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            return jsonify({
                'success': False,
                'message': 'SHARE身份记录不存在'
            }), 404
        
        # 获取身份记录
        identity_record = None
        if decoded_identity != 'SHARE':
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=decoded_identity).first()
            if not identity_record:
                return jsonify({
                    'success': False,
                    'message': '身份不存在'
                }), 404
        
        # 获取共用资料（SHARE）
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=share_identity.id
        ).first()
        
        # 获取特定身份资料
        specific_doc = None
        if identity_record and identity_record.id != share_identity.id:
            specific_doc = VisaDocuments.query.filter_by(
                visa_type_id=visa_type_record.id,
                singapore_identity_id=identity_record.id
            ).first()
        
        # 合并文档信息
        documents = []
        additional_info = []
        
        # 查询关联表中的准备方信息
        from sqlalchemy import text
        
        # 获取共用资料的准备方信息
        share_responsible_parties = {}
        if share_doc:
            sql = text("""
                SELECT document_id, responsible_party 
                FROM visa_document_documents 
                WHERE visa_document_id = :visa_doc_id
            """)
            result = db.session.execute(sql, {'visa_doc_id': share_doc.id})
            share_responsible_parties = {row.document_id: row.responsible_party for row in result}
        
        # 获取特定身份资料的准备方信息
        specific_responsible_parties = {}
        if specific_doc:
            sql = text("""
                SELECT document_id, responsible_party 
                FROM visa_document_documents 
                WHERE visa_document_id = :visa_doc_id
            """)
            result = db.session.execute(sql, {'visa_doc_id': specific_doc.id})
            specific_responsible_parties = {row.document_id: row.responsible_party for row in result}
        
        # 处理共用资料
        if share_doc and share_doc.selected_documents:
            for doc in share_doc.selected_documents:
                responsible_party = share_responsible_parties.get(doc.id, 'FOR_APPLICATION')
                documents.append({
                    'name': doc.name,
                    'type': 'document',
                    'category': '共用资料',
                    'is_shared': True,
                    'responsible_party': responsible_party
                })
        
        # 处理特定身份资料
        if specific_doc and specific_doc.selected_documents:
            for doc in specific_doc.selected_documents:
                responsible_party = specific_responsible_parties.get(doc.id, 'FOR_APPLICATION')
                documents.append({
                    'name': doc.name,
                    'type': 'document',
                    'category': '特定身份资料',
                    'is_shared': False,
                    'responsible_party': responsible_party
                })
        
        # 处理补充信息
        if share_doc and share_doc.additional_info and share_doc.additional_info.strip() and share_doc.additional_info != '待输入':
            additional_info.append({
                'content': share_doc.additional_info,
                'type': 'additional',
                'category': '共用补充信息'
            })
        
        if specific_doc and specific_doc.additional_info and specific_doc.additional_info.strip():
            additional_info.append({
                'content': specific_doc.additional_info,
                'type': 'additional',
                'category': '特定身份补充信息'
            })
        
        print(f"DEBUG: 解析后的文档数量: {len(documents)}")
        print(f"DEBUG: 解析后的补充信息数量: {len(additional_info)}")
        print(f"DEBUG: 共用资料数量: {len([d for d in documents if d['is_shared']])}")
        print(f"DEBUG: 特定身份资料数量: {len([d for d in documents if not d['is_shared']])}")
        
        return jsonify({
            'success': True,
            'documents': documents,
            'additional_info': additional_info,
            'share_count': len([d for d in documents if d['is_shared']]),
            'specific_count': len([d for d in documents if not d['is_shared']])
        })
        
    except Exception as e:
        current_app.logger.error(f"获取项目资料时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败：{str(e)}'
        }), 500


@visa_project.route('/test_japan_visa_data')
def test_japan_visa_data():
    """测试日本签证PR身份数据"""
    try:
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
        
        # 获取日本签证类型
        visa_type = VisaTypes.query.filter_by(visa_type='日本签证').first()
        if not visa_type:
            return jsonify({'error': '没有找到日本签证类型'})
        
        # 获取PR身份记录
        pr_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='PR').first()
        if not pr_identity:
            return jsonify({'error': '没有找到PR身份记录'})
        
        # 检查SHARE记录
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=None
        ).first()
        
        # 检查PR特定身份记录
        pr_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=pr_identity.id
        ).first()
        
        # 使用get_document_info方法
        pr_info = VisaDocuments.get_document_info(visa_type.id, pr_identity.id)
        
        result = {
            'visa_type': {
                'name': visa_type.visa_type,
                'id': visa_type.id
            },
            'pr_identity': {
                'name': pr_identity.identity_zh,
                'id': pr_identity.id
            },
            'share_record': {
                'exists': share_doc is not None,
                'id': share_doc.id if share_doc else None,
                'documents_count': len(share_doc.selected_documents) if share_doc and share_doc.selected_documents else 0,
                'documents': [doc.name for doc in share_doc.selected_documents] if share_doc and share_doc.selected_documents else [],
                'additional_info': share_doc.additional_info if share_doc else None
            },
            'pr_record': {
                'exists': pr_doc is not None,
                'id': pr_doc.id if pr_doc else None,
                'documents_count': len(pr_doc.selected_documents) if pr_doc and pr_doc.selected_documents else 0,
                'documents': [doc.name for doc in pr_doc.selected_documents] if pr_doc and pr_doc.selected_documents else [],
                'additional_info': pr_doc.additional_info if pr_doc else None
            },
            'get_document_info_result': pr_info
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})


@visa_project.route('/check_share_documents/<visa_type>')
def check_share_documents(visa_type):
    """检查SHARE记录的关联文档"""
    try:
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
        from sqlalchemy import text
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': f'签证类型 {visa_type} 不存在'})
        
        # 获取SHARE记录
        share_doc = VisaDocuments.query.filter_by(
            visa_type_id=visa_type_record.id,
            singapore_identity_id=None
        ).first()
        
        if not share_doc:
            return jsonify({'error': 'SHARE记录不存在'})
        
        # 直接查询关联表
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
        
        return jsonify({
            'visa_type': visa_type,
            'share_doc_id': share_doc.id,
            'associated_documents': associated_docs,
            'all_available_documents': all_docs_list,
            'message': f'SHARE记录关联了 {len(associated_docs)} 个文档'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})


@visa_project.route('/add_share_documents/<visa_type>', methods=['POST'])
@csrf.exempt
def add_share_documents(visa_type):
    """为SHARE记录添加常用文档"""
    try:
        from App_new.business.visa.models.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not visa_type_record:
            return jsonify({'error': f'签证类型 {visa_type} 不存在'})
        
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
            'success': True,
            'message': f'成功为SHARE记录添加了 {len(added_docs)} 个文档',
            'added_documents': added_docs
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


@visa_project.route('/update_document_status', methods=['POST'])
@csrf.exempt
def update_document_status():
    """更新资料准备状态"""
    try:
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        
        data = request.get_json()
        document_status_id = data.get('document_status_id')
        is_ready = data.get('is_ready')
        notes = data.get('notes', '')
        
        if document_status_id is None:
            return jsonify({
                'success': False,
                'message': '缺少资料状态ID'
            }), 400
            
        # 获取资料状态记录
        document_status = VisaProjectDocumentStatus.query.get(document_status_id)
        if not document_status:
            return jsonify({
                'success': False,
                'message': '资料状态记录不存在'
            }), 404
            
        # 更新状态
        document_status.is_ready = is_ready
        document_status.notes = notes
        document_status.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '资料状态更新成功',
            'data': document_status.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新资料状态时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新资料状态时出错：{str(e)}'
        }), 500


@visa_project.route('/sync_project_documents/<int:project_id>', methods=['POST'])
@csrf.exempt
def sync_project_documents(project_id):
    """同步项目资料清单（从模板获取并创建项目状态记录）"""
    try:
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus, VisaTypes, VisaSingaporeIdentity
        
        # 获取项目信息
        project = VisaProject.query.get_or_404(project_id)
        
        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        if not types_info:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 404
        
        # 获取SHARE身份记录
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 获取当前项目的资料状态
        existing_statuses = VisaProjectDocumentStatus.query.filter_by(project_id=project_id).all()
        existing_document_names = {status.document_name for status in existing_statuses}
        
        # 获取模板资料清单
        template_documents = []
        
        # 获取SHARE共用资料
        if share_identity_id:
            share_doc = VisaDocuments.query.filter_by(
                visa_type_id=types_info.id,
                singapore_identity_id=share_identity_id
            ).first()
            if share_doc and share_doc.selected_documents:
                for doc in share_doc.selected_documents:
                    template_documents.append({
                        'name': doc.name,
                        'type': 'document',
                        'category': 'SHARE'
                    })
        
        # 获取特定身份资料
        if project.singapore_status and project.singapore_status != 'SHARE':
            specific_doc = VisaDocuments.query.filter_by(
                visa_type_id=types_info.id,
                singapore_identity_id=share_identity_id
            ).first()
            if specific_doc and specific_doc.selected_documents:
                for doc in specific_doc.selected_documents:
                    template_documents.append({
                        'name': doc.name,
                        'type': 'document',
                        'category': project.singapore_status
                    })
        
        # 创建新的资料状态记录
        new_statuses = []
        for doc in template_documents:
            if doc['name'] not in existing_document_names:
                new_status = VisaProjectDocumentStatus(
                    project_id=project_id,
                    document_name=doc['name'],
                    document_type=doc['type'],
                    is_ready=False,
                    notes=''
                )
                db.session.add(new_status)
                new_statuses.append(new_status)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功同步 {len(new_statuses)} 个新资料',
            'new_count': len(new_statuses)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"同步项目资料时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'同步项目资料时出错：{str(e)}'
        }), 500


@visa_project.route('/add_custom_document/<int:project_id>', methods=['POST'])
@csrf.exempt
def add_custom_document(project_id):
    """为项目添加自定义资料"""
    try:
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        
        data = request.get_json()
        document_name = data.get('document_name')
        document_type = data.get('document_type', 'document')
        notes = data.get('notes', '')
        
        if not document_name:
            return jsonify({
                'success': False,
                'message': '缺少资料名称'
            }), 400
            
        # 检查是否已存在同名资料
        existing = VisaProjectDocumentStatus.query.filter_by(
            project_id=project_id,
            document_name=document_name
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': '该资料已存在'
            }), 400
        
        # 创建新的资料状态记录
        new_status = VisaProjectDocumentStatus(
            project_id=project_id,
            document_name=document_name,
            document_type=document_type,
            is_ready=False,
            notes=notes
        )
        
        db.session.add(new_status)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '自定义资料添加成功',
            'data': new_status.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"添加自定义资料时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'添加自定义资料时出错：{str(e)}'
        }), 500


@visa_project.route('/delete_document_status/<int:document_status_id>', methods=['DELETE', 'POST'])
@csrf.exempt
def delete_document_status(document_status_id):
    """删除资料状态记录"""
    try:
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        
        document_status = VisaProjectDocumentStatus.query.get_or_404(document_status_id)
        document_name = document_status.document_name
        
        db.session.delete(document_status)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'资料 "{document_name}" 已删除'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除资料状态时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除资料时出错：{str(e)}'
        }), 500


@visa_project.route('/get_documents_list', methods=['GET'])
def get_documents_list():
    from App_new.business.visa.models.Visamodels import VisaDocumentsList
    query = request.args.get('q', '').strip()
    q = VisaDocumentsList.query
    if query:
        q = q.filter(VisaDocumentsList.name.ilike(f'%{query}%'))
    docs = q.order_by(VisaDocumentsList.name.asc()).all()
    return jsonify([doc.name for doc in docs])


@visa_project.route('/test_visa_detail/<int:project_id>')
def test_visa_detail(project_id):
    """测试签证详情页面路由"""
    try:
        print(f"DEBUG: test_visa_detail called with project_id={project_id}")
        
        # 获取项目信息
        project = VisaProject.query.get(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        
        print(f"DEBUG: Found project: {project.project_folder_name}, visa_type={project.visa_type}")
        
        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        if not types_info:
            return jsonify({'error': f'签证类型不存在: {project.visa_type}'}), 404
        
        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'project_folder_name': project.project_folder_name,
                'visa_type': project.visa_type,
                'applicant_name': project.applicant_name
            },
            'visa_type': {
                'id': types_info.id,
                'visa_type': types_info.visa_type
            }
        })
        
    except Exception as e:
        print(f"DEBUG: Exception in test_visa_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500


@visa_project.route('/get_additional_info')
def get_additional_info():
    """获取签证类型的补充信息"""
    try:
        visa_type = request.args.get('visa_type')
        identity = request.args.get('identity')
        
        if not visa_type or not identity:
            return jsonify({
                'success': False,
                'message': '签证类型和身份参数不能为空'
            })
        
        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=visa_type).first()
        if not types_info:
            return jsonify({
                'success': False,
                'message': f'签证类型 "{visa_type}" 不存在'
            })
        
        # 获取身份信息
        from App_new.business.visa.models.Visamodels import VisaSingaporeIdentity, VisaDocuments
        identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=identity).first()
        if not identity_record:
            return jsonify({
                'success': False,
                'message': f'身份 "{identity}" 不存在'
            })
        
        # 获取共用资料补充信息
        share_info = VisaDocuments.get_document_info(types_info.id, None)
        share_additional_info = share_info.get('additional_info', '暂无补充信息') if share_info else '暂无补充信息'
        
        # 获取特定身份补充信息
        identity_info = VisaDocuments.get_document_info(types_info.id, identity_record.id)
        identity_additional_info = identity_info.get('additional_info', '暂无补充信息') if identity_info else '暂无补充信息'
        
        return jsonify({
            'success': True,
            'share_additional_info': share_additional_info,
            'identity_additional_info': identity_additional_info
        })
        
    except Exception as e:
        current_app.logger.error(f"获取补充信息时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取补充信息失败: {str(e)}'
        }), 500


@visa_project.route('/update_hid', methods=['POST'])
@csrf.exempt
def update_hid():
    """更新项目的HID编号"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        hid_number = data.get('hid_number', '').strip()
        
        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少项目ID'
            }), 400
        
        # 查找项目
        project = VisaProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404
        
        # 更新HID编号
        project.hid_or_serial = hid_number
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'HID编号更新成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"更新HID编号时发生错误: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新HID编号失败: {str(e)}'
        }), 500


@visa_project.route('/update_ref', methods=['POST'])
@csrf.exempt
def update_ref():
    """更新项目的Ref编号"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        ref_number = data.get('ref_number', '').strip()
        
        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少项目ID'
            }), 400
        
        # 查找项目
        project = VisaProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404
        
        # 更新Ref编号
        project.ref_number = ref_number
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ref编号更新成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"更新Ref编号时发生错误: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新Ref编号失败: {str(e)}'
        }), 500


@visa_project.route('/unlink_hid_ref', methods=['POST'])
@csrf.exempt
def unlink_hid_ref():
    """解除项目的HID和Ref编号关联"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少项目ID'
            }), 400
        
        # 查找项目
        project = VisaProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404
        
        # 解除HID关联
        if hasattr(project, 'header') and project.header:
            # 这里需要根据实际的数据库模型来解除关联
            # 假设有一个header_id字段
            project.header_id = None
        
        # 解除Ref关联
        if hasattr(project, 'ref') and project.ref:
            # 这里需要根据实际的数据库模型来解除关联
            # 假设有一个ref_id字段
            project.ref_id = None
        
        # 清空hid_or_serial和ref_number字段
        project.hid_or_serial = None
        project.ref_number = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'HID和Ref编号关联已解除'
        })
        
    except Exception as e:
        current_app.logger.error(f"解除HID和Ref编号关联时发生错误: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'解除关联失败: {str(e)}'
        }), 500

@visa_project.route('/add_link/<int:project_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def add_link(project_id):
    """为项目添加相关链接"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 获取表单数据
        visa_type_id = request.form.get('visa_type_id', '').strip()
        visa_countries_id = request.form.get('visa_countries_id', '').strip()
        link_name = request.form.get('link_name', '').strip()
        link_url = request.form.get('link_url', '').strip()
        
        if not visa_type_id or not visa_countries_id or not link_name or not link_url:
            return jsonify({
                'success': False,
                'message': '请填写完整的链接信息'
            }), 400
        
        # 验证URL格式
        if not link_url.startswith(('http://', 'https://')):
            link_url = 'https://' + link_url
        
        # 验证签证类型和国家ID
        visa_type = VisaTypes.query.get(visa_type_id)
        if not visa_type:
            return jsonify({
                'success': False,
                'message': f'签证类型ID {visa_type_id} 不存在'
            }), 400
            
        country = VisaCountries.query.get(visa_countries_id)
        if not country:
            return jsonify({
                'success': False,
                'message': f'国家ID {visa_countries_id} 不存在'
            }), 400
        
        # 创建新链接
        new_link = VisaLinks(
            name=link_name,
            link=link_url,
            visa_type_id=int(visa_type_id),
            visa_countries_id=int(visa_countries_id)
        )
        
        db.session.add(new_link)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '链接添加成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"添加链接时发生错误: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'添加链接失败: {str(e)}'
        }), 500

@visa_project.route('/delete_link/<int:link_id>', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_link(link_id):
    """删除相关链接"""
    try:
        link = VisaLinks.query.get_or_404(link_id)
        
        db.session.delete(link)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '链接删除成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"删除链接时发生错误: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除链接失败: {str(e)}'
        }), 500


# ==================== 文件上传管理 ====================

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'txt', 'zip', 'rar'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@visa_project.route('/api/files/<int:project_id>', methods=['GET'])
@login_required
@staff_only
def get_project_files(project_id):
    """获取项目的所有上传文件"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        files = VisaProjectFile.query.filter_by(project_id=project_id).order_by(VisaProjectFile.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'files': [{
                'id': f.id,
                'file_name': f.file_name,
                'file_type': f.file_type,
                'file_size': f.get_file_size_display(),
                'description': f.description,
                'uploaded_by': f.uploaded_by,
                'created_at': f.created_at.strftime('%Y-%m-%d %H:%M') if f.created_at else ''
            } for f in files]
        })
    except Exception as e:
        current_app.logger.error(f"获取项目文件列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@visa_project.route('/api/files/<int:project_id>/upload', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def upload_project_file(project_id):
    """上传项目文件"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': f'不支持的文件类型，支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # 获取文件信息
        original_filename = file.filename
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # 创建上传目录
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'visa_projects', str(project_id))
        os.makedirs(upload_folder, exist_ok=True)
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = secure_filename(original_filename)
        new_filename = f"{timestamp}_{safe_filename}"
        file_path = os.path.join(upload_folder, new_filename)
        
        # 保存文件
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # 获取描述
        description = request.form.get('description', '')
        
        # 创建数据库记录
        project_file = VisaProjectFile(
            project_id=project_id,
            file_name=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_ext,
            description=description,
            uploaded_by=current_user.username if current_user else None
        )
        db.session.add(project_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file': {
                'id': project_file.id,
                'file_name': project_file.file_name,
                'file_type': project_file.file_type,
                'file_size': project_file.get_file_size_display(),
                'description': project_file.description,
                'uploaded_by': project_file.uploaded_by,
                'created_at': project_file.created_at.strftime('%Y-%m-%d %H:%M') if project_file.created_at else ''
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"上传文件失败: {str(e)}\n{traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@visa_project.route('/api/files/<int:file_id>/delete', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def delete_project_file(file_id):
    """删除项目文件"""
    try:
        project_file = VisaProjectFile.query.get_or_404(file_id)
        
        # 删除物理文件
        if project_file.file_path and os.path.exists(project_file.file_path):
            os.remove(project_file.file_path)
        
        # 删除数据库记录
        db.session.delete(project_file)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '文件删除成功'})
        
    except Exception as e:
        current_app.logger.error(f"删除文件失败: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@visa_project.route('/api/files/<int:file_id>/download')
@login_required
@staff_only
def download_project_file(file_id):
    """下载项目文件"""
    from flask import send_file
    try:
        project_file = VisaProjectFile.query.get_or_404(file_id)
        
        if not os.path.exists(project_file.file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        return send_file(
            project_file.file_path,
            as_attachment=True,
            download_name=project_file.file_name
        )
        
    except Exception as e:
        current_app.logger.error(f"下载文件失败: {str(e)}")
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500