import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import os
from datetime import datetime
from pathlib import Path
import platform
import subprocess
from ..exts import db
from ..models import VisaTypes, VisaDocuments, VisaLinks, VisaProject
from ..code.VisaForm import VisasUtils
import json
import traceback
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightSchedule, AirportData
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import re
from urllib.parse import unquote


"""
项目管理 (visa_project.py):
项目列表 (/visa/project/show_current_all_projects)
项目处理 (/visa/project/visa_processing/<country>)
项目详情 (/visa/project/detail/<project_id>)

"""
# 创建蓝图
visa_project = Blueprint('visa_project', __name__, url_prefix='/visa/project')

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
    """显示所有签证项目"""
    try:
        # 获取筛选和排序参数
        visa_status = request.args.get('visa_status', 'pending_submission')
        sort_by = request.args.get('sort_by', 'created_date')
        filter_visa_type = request.args.get('filter_visa_type', 'all')
        applicant_name = request.args.get('applicant_name', '').strip()

        # 构建基础查询
        query = VisaProject.query

        # 添加状态筛选
        if visa_status != 'all':
            if visa_status == 'pending_submission':
                query = query.filter(VisaProject.visa_status == '待递交')
            elif visa_status == 'submitted':
                query = query.filter(VisaProject.visa_status == '待出签')
            elif visa_status == 'approved':
                query = query.filter(VisaProject.visa_status == '已出签')
            elif visa_status == 'ignored':
                query = query.filter(VisaProject.visa_status == '忽略单')

        # 添加签证类型筛选
        if filter_visa_type != 'all':
            query = query.filter(VisaProject.visa_type == filter_visa_type)

        # 添加申请人名字搜索
        if applicant_name:
            query = query.filter(VisaProject.applicant_name.ilike(f'%{applicant_name}%'))

        # 获取签证类别
        visa_categories = VisaTypes.query.all()

        # 排除特定签证类型的项目（如有需求）
        visa_type_names = VisaTypes.query.with_entities(VisaTypes.visa_type).all()
        excluded_types = [name[0] for name in visa_type_names]
        if excluded_types:
            query = query.filter(~VisaProject.project_folder_name.in_(excluded_types))

        # 添加排序
        if sort_by == 'name':
            query = query.order_by(VisaProject.project_name)
        else:  # sort_by == 'created_date'
            query = query.order_by(VisaProject.created_date.desc())

        # 执行查询
        projects = query.all()

        # 将查询结果转为字典格式
        projects_data = [
            {
                "id": project.id,
                "name": project.project_folder_name,
                "project_folder_name": project.project_folder_name,
                "created_date": project.created_date,
                "visa_status": project.visa_status,
                "estimated_date": project.estimated_date,
                "visa_type": project.visa_type,
                "applicant_name": project.applicant_name,
                "contact_name": project.contact_name,
                "remarks": project.remarks,
                "hid_or_serial": project.hid_or_serial,
                "singapore_status": project.singapore_status
            }
            for project in projects
        ]

        return render_template('visas/签证项目管理.html',
                           projects=projects_data,
                           visa_status=visa_status,
                           sort_by=sort_by,
                           filter_visa_type=filter_visa_type,
                           visa_categories=visa_categories)

    except Exception as e:
        flash(f'获取签证项目列表时出错：{str(e)}', 'error')
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
        types_info = VisaTypes.query.filter_by(visa_type=visa_type).first_or_404()
        
        # 获取相关链接
        links = VisaLinks.query.filter_by(visa_type=visa_type).order_by(VisaLinks.name.asc()).all()

        # 获取签证文档数据
        documents = VisaDocuments.query.filter_by(visa_type=visa_type).all()
        document_data = {}
        
        # 获取共用资料
        common_doc = VisaDocuments.query.filter_by(
            visa_type=visa_type,
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
        projects = [item for item in project_list if visa_type in item]

        return render_template('visas/签证项目创建.html',
                             form_data=form_data,
                             visa_type=visa_type,
                             types_info=types_info,
                             links=links,
                             projects=projects,
                             document_data=document_data)
                             
    except json.JSONDecodeError:
        flash('表单数据格式错误', 'error')
        return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))
    except Exception as e:
        flash(f'处理签证信息时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.visa_processing', visa_type=visa_type))

@visa_project.route('/delete_current_project/<int:project_id>', methods=['POST'])
def delete_current_project(project_id):

    try:
        project = VisaProject.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True, "message": "项目删除成功！"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@visa_project.route('/update_project/<int:project_id>', methods=['GET', 'POST'])
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
    return render_template('visas/现有签证项目管理.html', project=project)


@visa_project.route('/edit_project/<int:project_id>', methods=['GET'])
def edit_project(project_id):
    """显示签证项目编辑页面"""
    project = VisaProject.query.get_or_404(project_id)
    return render_template('visas/签证项目编辑.html', project=project)


@visa_project.route('/generate_form/<int:project_id>', methods=['POST'])
def generate_form_for_project(project_id):
    """为项目生成表格"""
    try:
        project = VisaProject.query.get_or_404(project_id)
        
        # 生成表格的逻辑...
        
        return jsonify({'success': True, 'message': '表格生成成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


""" 签证详细 开始 """
@visa_project.route('/project_detail/<int:project_id>')
@visa_project.route('/detail/<int:project_id>')  # 保留旧路由以保持兼容性
def visa_detail(project_id):
    """显示签证项目详情页面"""
    # 获取当前的visa_status和sort_by参数
    visa_status = request.args.get('visa_status', 'all')
    sort_by = request.args.get('sort_by', 'created_date')
    
    # 从数据库获取项目信息
    project = VisaProject.query.get_or_404(project_id)
    
    # 获取签证文档数据
    document_data = {}
    
    # 获取共用资料
    common_doc = VisaDocuments.query.filter_by(
        visa_type=project.visa_type,
        singapore_identity='SHARE'
    ).first()
    
    # 获取特定身份的文档
    specific_doc = VisaDocuments.query.filter_by(
        visa_type=project.visa_type,
        singapore_identity=project.singapore_status
    ).first()

    # 处理文档数据
    if specific_doc or common_doc:
        document_info = []
        additional_info = []
        
        # 添加共用资料（如果存在）
        if common_doc and common_doc.document_info:
            document_info.append(common_doc.document_info)
        if common_doc and common_doc.additional_info:
            additional_info.append(common_doc.additional_info)
        
        # 添加特定身份资料
        if specific_doc:
            if specific_doc.document_info:
                if document_info:  # 如果已有共用资料，添加换行符
                    document_info.append("\n")
                document_info.append(specific_doc.document_info)
            if specific_doc.additional_info:
                if additional_info:  # 如果已有共用资料的补充信息，添加换行符
                    additional_info.append("\n")
                additional_info.append(specific_doc.additional_info)
        
        document_data[project.singapore_status] = {
            'document_info': "\n".join(document_info) if document_info else None,
            'additional_info': "\n".join(additional_info) if additional_info else None
        }

    # 获取相关链接
    links = VisaLinks.query.filter_by(visa_type=project.visa_type).order_by(VisaLinks.name.asc()).all()
    
    return render_template('visas/签证项目详细.html',
                         project=project,
                         document_data=document_data,
                         links=links,
                         visa_status=visa_status,
                         sort_by=sort_by)


@visa_project.route('/update_visa_status/<int:project_id>', methods=['POST'])
def update_visa_status(project_id):
    try:
        # 获取新的签证状态
        new_status = request.form.get('visa_status')
        if not new_status:
            return jsonify({'success': False, 'message': '未提供签证状态'}), 400

        # 获取项目
        project = VisaProject.query.get_or_404(project_id)
        
        # 更新状态
        project.visa_status = new_status
        db.session.commit()

        # 返回更新后的项目数据
        return jsonify({
            'success': True,
            'message': '签证状态更新成功',
            'project': {
                'id': project.id,
                'visa_status': project.visa_status,
                'estimated_date': project.estimated_date
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@visa_project.route('/update_status/<int:project_id>', methods=['POST'])
def update_project_status(project_id):
    try:
        data = request.get_json()
        project = VisaProject.query.get_or_404(project_id)
        
        # 验证状态值
        valid_statuses = ['待递交', '待出签', '已出签', '忽略单']
        new_status = data.get('visa_status')
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': '无效的状态值'
            }), 400
            
        # 更新状态
        project.visa_status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '状态更新成功',
            'visa_status': new_status
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新签证状态时发生错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'更新状态失败: {str(e)}'
        }), 500


@visa_project.route('/<visa_type>/visa_create_project', methods=['POST'])
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
                static_path = os.path.join(current_app.root_path, 'static')
                VisasUtils.korea_visa_fill_form(visa_folder=visa_folder, static_path=static_path)

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
        visa_folder = os.path.join(current_app.root_path, 'static', '资源', 'Project',
                                   'Visa')  # static\资源\Project\Visa\韩国签证_HID169764_LUO XINFEI_工作准证
        project_file_name = f"{project_name}_{singapore_status}"
        project_folder = os.path.join(visa_folder, project_file_name)
        os.makedirs(project_folder, exist_ok=True)

        "b 将资源文件夹内容复制到创建项目文件夹"
        source_path = os.path.join(current_app.root_path, 'static', "资源", "签证", visa_type)  # 韩国签证 资源文件，储存表格及表格坐标
        share_path = os.path.join(source_path, '共用资料')  # 共用资料文件夹复制到指定文件夹  static\资源\签证\韩国签证\共用资料
        id_path = os.path.join(source_path, singapore_status)  # 身份文件夹资料 复制到 指定文件夹  static\资源\签证\韩国签证\PR

        folders = [share_path, id_path]

        for file_path in folders:
            # 检查路径是否存在，如果不存在则创建
            if not os.path.exists(file_path):
                print(f"Creating directory: {file_path}")
                os.makedirs(file_path)

            # 复制源文件夹中的文件
            for file in os.listdir(file_path):
                src_path = os.path.join(file_path, file)
                dst_path = os.path.join(project_folder, file)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f"Copied file: {src_path} -> {dst_path}")

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

        # 获取项目根目录
        project_root = Path(__file__).resolve().parent.parent

        # 根据文件夹类型构建路径
        if folder_type == 'project' and project_folder and visa_type:
            base_folder = project_root / "static" / "资源" / "Project" / "Visa"
            # 首先尝试在签证类型子文件夹中查找
            folder_path = base_folder / visa_type / project_folder
            if not folder_path.exists():
                # 如果不存在，尝试在根目录中查找
                folder_path = base_folder / project_folder

            if not folder_path.exists():
                return jsonify({
                    "success": False, 
                    "message": f"找不到项目文件夹：{project_folder}"
                }), 404

        elif folder_type == 'visa_type' and visa_type:
            # 修改为正确的签证类型资源文件夹路径
            folder_path = project_root / "static" / "资源" / "签证" / visa_type
            if not folder_path.exists():
                return jsonify({
                    "success": False, 
                    "message": f"找不到签证类型文件夹：{visa_type}"
                }), 404

        elif folder_type == 'visa_root':
            # 修改为正确的签证根目录路径
            folder_path = project_root / "static" / "资源" / "签证"
            if not folder_path.exists():
                return jsonify({
                    "success": False, 
                    "message": "找不到签证根目录"
                }), 404

        else:
            return jsonify({
                "success": False, 
                "message": "无效的文件夹类型或参数缺失"
            }), 400

        # 转换为字符串路径
        folder_path_str = str(folder_path)

        # 打印调试信息
        print(f"Opening folder: {folder_path_str}")
        print(f"Folder exists: {os.path.exists(folder_path_str)}")

        # 根据操作系统打开文件夹
        if platform.system() == "Windows":
            os.startfile(folder_path_str)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path_str])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path_str])

        return jsonify({
            "success": True, 
            "message": "文件夹已打开",
            "path": folder_path_str  # 返回实际打开的路径，方便调试
        })

    except Exception as e:
        print(f"Error opening folder: {str(e)}")  # 添加服务器端日志
        return jsonify({
            "success": False, 
            "message": f"打开文件夹时出错：{str(e)}"
        }), 500

