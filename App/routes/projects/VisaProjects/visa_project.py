import shutil
from flask import current_app
import os
from datetime import datetime
import platform
import subprocess
from App.exts import db, csrf
from App.models import VisaTypes, VisaDocuments, VisaLinks, VisaProject, VisaCountries, VisaSingaporeIdentity
from App.code.VisaForm import VisasUtils
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
    return visa_type in SUPPORTED_FORM_GENERATION_VISA_TYPES

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

@visa_project.route('/show_current_all_projects')
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

        # 构建基础查询
        query = VisaProject.query

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

        return render_template('visas/签证项目管理/签证项目列表.html',
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

        # 获取所有身份
        from App.models.Product.Visamodels import VisaSingaporeIdentity, VisaDocuments
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        document_data = {}
        for identity in identities:
            info = VisaDocuments.get_document_info(types_info.id, identity.id)
            document_data[identity.identity_zh] = info
        # 处理共用资料
        share_info = VisaDocuments.get_document_info(types_info.id, None)
        document_data['SHARE'] = share_info

        # 获取项目列表
        from App.config import Config
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

        return render_template('visas/签证项目管理/签证项目创建.html',
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
@csrf.exempt
def delete_current_project(project_id):
    try:
        # 获取项目信息
        project = VisaProject.query.get_or_404(project_id)
        project_folder_name = project.project_folder_name
        visa_type = project.visa_type

        # 构建项目文件夹路径
        from App.config import Config
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
    return render_template('visas/签证项目管理/签证项目管理.html', project=project)


@visa_project.route('/edit_project/<int:project_id>', methods=['GET'])
def edit_project(project_id):
    """显示签证项目编辑页面"""
    project = VisaProject.query.get_or_404(project_id)
    return render_template('visas/签证项目管理/签证项目编辑.html', project=project)


@visa_project.route('/generate_form/<int:project_id>', methods=['POST'])
@csrf.exempt
def generate_form_for_project(project_id):
    """为项目生成表格"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 检查签证类型是否支持表格生成
        if not is_visa_type_supported_for_form_generation(project.visa_type):
            return jsonify({
                'success': False, 
                'message': f'签证类型 "{project.visa_type}" 暂不支持表格生成功能'
            }), 400
        
        # 生成表格的逻辑
        project_name = f"{project.visa_type}_{project.hid_or_serial}_{project.applicant_name}"
        visa_folder = f"{project_name}_{project.singapore_status}"
        from App.config import Config
        static_path = Config.PROJECT_ROOT / "App" / "static"
        
        # 根据签证类型调用相应的表格生成函数
        if '韩国' in project.visa_type:
            # 调用韩国签证表格生成函数
            from App.code.VisaForm import VisasUtils
            VisasUtils.korea_visa_fill_form(visa_folder=visa_folder, static_path=str(static_path))
        else:
            return jsonify({
                'success': False, 
                'message': f'签证类型 "{project.visa_type}" 的表格生成功能尚未实现'
            }), 400
        
        return jsonify({'success': True, 'message': '表格生成成功'})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'message': f'文件或目录不存在: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"生成表格时发生错误: {str(e)}")
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
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
        
        return render_template('visas/签证项目管理/签证项目详细.html',
                             project=project,
                             types_info=types_info,
                             links=links,
                             document_data=document_data,
                             document_statuses=document_statuses)
                             
    except Exception as e:
        print(f"DEBUG: Exception in visa_detail: {str(e)}")
        print(f"DEBUG: Exception traceback: {traceback.format_exc()}")
        flash(f'获取签证详情时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))


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

        # 验证必填字段
        if not hid_or_serial or not applicant_name or not visa_type_input or not singapore_status or not visa_status or not estimated_date:
            error_msg = "缺少必要的项目信息，请确保所有必填字段已填写"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            flash(error_msg, 'error')
            return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

        # 自动生成项目名称
        project_name = f"{visa_type_input}_{hid_or_serial}_{applicant_name}"

        # 如果是生成表格，直接重定向到处理页面
        if submit_button == 'generate_form':
            try:
                visa_folder = f"{project_name}_{singapore_status}"
                from App.config import Config
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
        from App.config import Config
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
        new_project.hid_or_serial = hid_or_serial
        new_project.singapore_status = singapore_status

        db.session.add(new_project)
        db.session.flush()  # 获取项目ID
        
        # 保存资料状态数据
        if document_statuses:
            from App.models.Product.Visamodels import VisaProjectDocumentStatus
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
                'redirect_url': url_for('visa_project.edit_project', project_id=new_project.id)
            })

        # 否则重定向到项目编辑页面
        flash(f'项目创建成功: {project_file_name}', 'success')
        return redirect(url_for('visa_project.edit_project', project_id=new_project.id))

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

        # 验证必填字段
        if not all([hid_or_serial, visa_type, applicant_name, visa_status, singapore_status, estimated_date]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': '缺少必要的项目信息，请确保所有必填字段已填写'
                }), 400
            flash('缺少必要的项目信息，请确保所有必填字段已填写', 'error')
            return redirect(url_for('visa_project.edit_project', project_id=project_id))

        # 更新项目数据
        project.hid_or_serial = hid_or_serial
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
        from App.config import Config

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
                return jsonify({
                    "success": False, 
                    "message": f"找不到项目文件夹：{project_folder}"
                }), 404

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
        from App.config import Config
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
        
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
        from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
        
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
        from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity
        
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
        from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
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
        from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaDocumentsList
        
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
        
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus, VisaTypes, VisaSingaporeIdentity
        
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
        
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
        from App.models.Product.Visamodels import VisaProjectDocumentStatus
        
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
    from App.models.Product.Visamodels import VisaDocumentsList
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

