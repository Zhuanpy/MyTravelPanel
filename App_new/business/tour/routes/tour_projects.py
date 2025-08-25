from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from ....exts import db, csrf
from ..models.TourProject import TourGroup, TourItinerary, TourProject
from ..models.Packagemodels import CompanyInfo
from datetime import datetime
import os
import sys
import subprocess
import urllib.parse
import html
import logging
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError

# 创建蓝图
tour_projects = Blueprint('tour_projects', __name__)

def create_folder(base_path, folder_name):
    """创建文件夹的辅助函数"""
    folder_path = os.path.join(base_path, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

@tour_projects.route('/create', methods=['GET', 'POST'])
@csrf.exempt
def create_tour_project():
    """创建旅游项目页面"""
    if request.method == 'POST':
        try:
            print("=== 收到POST请求 ===")
            print(f"表单数据: {dict(request.form)}")
            print(f"请求头: {dict(request.headers)}")
            
            # 从前端表单中获取用户输入的数据
            project_name = request.form.get('projectName', '').strip()  # 项目名称
            project_hid = request.form.get('projectHID', '').strip()  # 项目HID（可选）
            project_type = request.form.get('projectType', '').strip()  # 项目类型
            budget_value = request.form.get('budget', '').strip()  # 项目预算
            departure_date = request.form.get('departureDate', '').strip()  # 出发日期
            project_status = request.form.get('projectStatus', '').strip()  # 项目状态
            contact_person = request.form.get('contactPerson', '').strip()  # 联系人
            contact_info = request.form.get('contactInfo', '').strip()  # 联系方式
            remarks = request.form.get('remarks', '').strip()  # 备注
            creation_date = datetime.now().date()

            print(f"解析后的数据:")
            print(f"  project_name: '{project_name}'")
            print(f"  project_hid: '{project_hid}'")
            print(f"  project_type: '{project_type}'")
            print(f"  budget_value: '{budget_value}'")
            print(f"  departure_date: '{departure_date}'")
            print(f"  project_status: '{project_status}'")
            print(f"  contact_person: '{contact_person}'")
            print(f"  contact_info: '{contact_info}'")
            print(f"  remarks: '{remarks}'")

            # 验证必填字段是否完整
            required_fields = [project_name, departure_date, project_status, contact_person]
            print(f"必填字段检查: {required_fields}")
            print(f"所有字段都有值: {all(required_fields)}")
            
            if not all(required_fields):
                missing_fields = []
                if not project_name: missing_fields.append('项目名称')
                if not departure_date: missing_fields.append('出发日期')
                if not project_status: missing_fields.append('项目状态')
                if not contact_person: missing_fields.append('联系人')
                
                error_msg = f'缺少必填字段: {", ".join(missing_fields)}'
                print(f"验证失败: {error_msg}")
                flash(error_msg, 'error')
                return redirect(url_for('tour_projects.create_tour_project'))

            # 验证出发日期格式
            try:
                formatted_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
                print(f"日期解析成功: {formatted_date}")
            except ValueError as e:
                print(f"日期解析失败: {e}")
                flash('出发日期格式无效，请选择有效的日期', 'error')
                return redirect(url_for('tour_projects.create_tour_project'))

            # 创建文件夹路径
            from ....config import Config
            tour_project_path = Config.TOUR_PROJECTS_PATH
            print(f"项目路径: {tour_project_path}")

            # 构建文件夹名称，增强可读性
            if project_hid:
                folder_name = f"{creation_date}_{project_hid}_{project_name}"
            else:
                folder_name = f"{creation_date}_{project_name}"
            
            print(f"文件夹名称: {folder_name}")

            # 创建文件夹（文件夹已存在则不会创建）
            create_folder(tour_project_path, folder_name)

            # 处理预算字段
            budget = None
            if budget_value:
                try:
                    budget = float(budget_value)
                    print(f"预算转换成功: {budget}")
                except ValueError:
                    budget = None
                    print(f"预算转换失败，设置为None")
            else:
                budget = None
                print(f"预算为空，设置为None")
            
            # 创建 TourProject 实例，准备保存到数据库
            new_project = TourProject(
                project_name=project_name,
                project_hid=project_hid if project_hid else None,  # 如果没有项目HID，则为 None
                project_type=project_type,
                budget=budget,
                project_status=project_status,
                folder_name=folder_name,
                contact_person=contact_person,
                contact_info=contact_info,
                remarks=remarks,
                departure_date=formatted_date
            )

            print("TourProject实例创建成功")

            # 将新项目添加到数据库会话
            db.session.add(new_project)

            # 提交到数据库
            db.session.commit()
            print("数据库提交成功")

            flash('旅游项目创建成功！', 'success')
            return redirect(url_for('tour_projects.manage_tour_projects'))

        except Exception as e:
            # 记录其他错误日志
            print(f"发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            logging.error(f"数据库操作失败: {e}")
            flash('创建旅游项目失败，请稍后重试', 'error')
            return redirect(url_for('tour_projects.create_tour_project'))

    # 不要传入与模板全局函数同名的 csrf_token，避免覆盖导致 'str' object is not callable
    return render_template('projects/TourProjects/tour_project_create.html')

@tour_projects.route('/manage', methods=['GET'])
def manage_tour_projects():
    """管理旅游项目页面"""
    # 获取表单参数（如果没有则使用默认值）
    travel_status = request.args.get('travel_status', '处理中')  # 默认显示"处理中"状态
    # 默认按创建时间倒序排列（最新在前）
    sort_by = request.args.get('sort_by', 'created_date')
    order = request.args.get('order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 15

    # 构建查询条件
    query = TourProject.query

    # 筛选旅游项目状态
    if travel_status == 'all':
        # 排除忽略单
        query = query.filter(TourProject.project_status != '忽略单')
    elif travel_status:
        query = query.filter(TourProject.project_status == travel_status)

    # 排序方式
    if sort_by == 'name':
        column = TourProject.project_name
    elif sort_by == 'created_date':
        column = TourProject.created_at
    else:
        # 默认按创建时间排序
        column = TourProject.created_at

    # 排序顺序
    if order == 'asc':
        query = query.order_by(column.asc())
    elif order == 'desc':
        query = query.order_by(column.desc())

    # 分页获取符合条件的项目
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    tour_projects = pagination.items

    return render_template('projects/TourProjects/tour_project_list.html',
                         projects=tour_projects,
                         pagination=pagination,
                         travel_status=travel_status, 
                         sort_by=sort_by, 
                         order=order)

@tour_projects.route('/update/<int:project_id>', methods=['POST'])
@csrf.exempt
def update_tour_project(project_id):
    """更新旅游项目"""
    try:
        project = TourProject.get_by_id(project_id)
        if not project:
            flash('项目不存在', 'error')
            return redirect(url_for('tour_projects.manage_tour_projects'))

        project.project_status = request.form.get("project_status")
        project.contact_person = request.form.get("contact_person")
        project.contact_info = request.form.get("contact_info")
        project.remarks = request.form.get("remarks")
        project.project_hid = request.form.get("project_hid")
        
        # 处理预算字段
        budget_value = request.form.get("budget", "").strip()
        if budget_value:
            try:
                project.budget = float(budget_value)
            except ValueError:
                project.budget = None
        else:
            project.budget = None
        
        # 保存更新到数据库
        project.save()

        flash('项目更新成功！', 'success')

    except Exception as e:
        flash(f'更新失败：{str(e)}', 'error')

    # 获取筛选参数
    current_status = request.form.get('current_travel_status', 'all')
    current_sort_by = request.form.get('current_sort_by', 'created_date')
    current_order = request.form.get('current_order', 'desc')
    current_page = request.form.get('current_page', 1, type=int)

    # 返回更新后的页面，并保持当前筛选状态
    return redirect(url_for('tour_projects.manage_tour_projects',
                          travel_status=current_status,
                          sort_by=current_sort_by,
                          order=current_order,
                          page=current_page))

@tour_projects.route('/delete/<int:project_id>', methods=['POST'])
@csrf.exempt
def delete_tour_project(project_id):
    """删除旅游项目"""
    try:
        project = TourProject.query.get(project_id)
        if not project:
            return jsonify({"success": False, "message": "项目不存在"}), 404

        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True, "message": "项目删除成功"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@tour_projects.route('/open_folder', methods=['GET', 'POST'])
def open_tour_project_folder():
    """打开旅游项目文件夹"""
    folder_name = request.args.get('folder_name', '')
    # 解码 URL
    folder_name = urllib.parse.unquote(folder_name)
    # 处理 HTML 实体
    folder_name = html.unescape(folder_name)

    # 使用配置中的路径
    from ....config import Config
    file_path = Config.TOUR_PROJECTS_PATH / folder_name

    # 检查文件夹是否存在
    if file_path.exists():
        if sys.platform == "win32":
            try:
                # 使用 explorer 命令打开文件夹
                subprocess.run(['explorer', str(file_path)], shell=True)
                
                # 等待一下让窗口打开，然后强制置顶
                import time
                time.sleep(0.3)
                
                # 使用 PowerShell 强制置顶窗口
                ps_script = f'''
                Add-Type -TypeDefinition @"
                using System;
                using System.Runtime.InteropServices;
                using System.Diagnostics;
                
                public class Win32 {{
                    [DllImport("user32.dll")]
                    [return: MarshalAs(UnmanagedType.Bool)]
                    public static extern bool SetForegroundWindow(IntPtr hWnd);
                    
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    
                    [DllImport("user32.dll")]
                    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
                    
                    [DllImport("user32.dll")]
                    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
                    
                    public const int SW_RESTORE = 9;
                    public const int SW_SHOW = 5;
                    public const uint SWP_NOMOVE = 0x0002;
                    public const uint SWP_NOSIZE = 0x0001;
                    public const uint SWP_SHOWWINDOW = 0x0040;
                    public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
                }}
"@
                
                # 查找所有 explorer 进程
                $explorers = Get-Process explorer -ErrorAction SilentlyContinue
                foreach ($explorer in $explorers) {{
                    if ($explorer.MainWindowHandle -ne [IntPtr]::Zero) {{
                        $title = $explorer.MainWindowTitle
                        if ($title -and $title -ne "") {{
                            Write-Host "Found explorer window: $title"
                            # 强制置顶窗口
                            [Win32]::ShowWindow($explorer.MainWindowHandle, [Win32]::SW_RESTORE)
                            [Win32]::SetForegroundWindow($explorer.MainWindowHandle)
                            [Win32]::SetWindowPos($explorer.MainWindowHandle, [Win32]::HWND_TOPMOST, 0, 0, 0, 0, [Win32]::SWP_NOMOVE -bor [Win32]::SWP_NOSIZE -bor [Win32]::SWP_SHOWWINDOW)
                            break
                        }}
                    }}
                }}
                '''
                
                # 执行 PowerShell 脚本
                subprocess.run(['powershell', '-Command', ps_script], shell=True, capture_output=True, text=True)
                
            except Exception as e:
                print(f"打开文件夹时出错: {e}")
                # 如果出错，回退到基本方法
                subprocess.run(['explorer', str(file_path)], shell=True)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, str(file_path)])  # 在 macOS 或 Linux 上打开文件夹
        return jsonify({"success": True, "message": "文件夹已成功打开"})
    else:
        return jsonify({"success": False, "message": f"文件夹不存在: {file_path}"}), 404

# 新增：行程团管理相关路由
@tour_projects.route('/groups', methods=['GET'])
def list_tour_groups():
    """列出所有行程团"""
    groups = TourGroup.query.order_by(TourGroup.created_at.desc()).all()
    return render_template('projects/TourProjects/tour_groups.html', groups=groups)

@tour_projects.route('/create_tour_group/<int:project_id>', methods=['POST'])
@csrf.exempt
def create_tour_group(project_id):
    """创建新的行程团"""
    try:
        print(f"收到创建团请求，project_id: {project_id}")
        print(f"表单数据: {dict(request.form)}")
        print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        # 验证项目是否存在
        project = TourProject.query.get_or_404(project_id)
        
        # 创建新团
        new_group = TourGroup(
            title=request.form.get('title'),
            departure_date=datetime.strptime(request.form.get('departure_date'), '%Y-%m-%d').date(),
            return_date=datetime.strptime(request.form.get('return_date'), '%Y-%m-%d').date(),
            pax=int(request.form.get('pax')),
            agency=request.form.get('agency'),
            operator=request.form.get('operator'),
            hotel_info=request.form.get('hotel_info'),
            project_id=project_id,
            created_by=request.form.get('created_by'),
            group_code=request.form.get('group_code'),
            group_status=request.form.get('group_status'),
            transport=request.form.get('transport'),
            meals=request.form.get('meals'),
            attractions=request.form.get('attractions'),
            included_items=request.form.get('included_items'),
            excluded_items=request.form.get('excluded_items'),
            important_notes=request.form.get('important_notes')
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        print("团创建成功")
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '新团创建成功'})
        else:
            flash('新团创建成功！', 'success')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
            
    except Exception as e:
        print(f"创建团失败: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        else:
            flash(f'创建失败：{str(e)}', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))

@tour_projects.route('/groups/<int:group_id>', methods=['GET'])
def view_tour_group(group_id):
    """查看行程团详情"""
    group = TourGroup.query.get_or_404(group_id)
    itineraries = TourItinerary.query.filter_by(tour_id=group_id).order_by(TourItinerary.date.asc()).all()
    company = CompanyInfo.query.first()
    current_time = datetime.now()
    return render_template('projects/TourProjects/tour_project_print_confirmation.html',
                         tour=group, 
                         itinerary=itineraries,
                         company=company,
                         current_time=current_time)

@tour_projects.route('/groups/<int:group_id>/itinerary', methods=['GET'])
def view_tour_itinerary(group_id):
    """查看行程单（仅包含每日行程安排和价格信息）"""
    group = TourGroup.query.get_or_404(group_id)
    itineraries = TourItinerary.query.filter_by(tour_id=group_id).order_by(TourItinerary.date.asc()).all()
    company = CompanyInfo.query.first()
    current_time = datetime.now()
    return render_template('projects/TourProjects/tour_project_print_itinerary.html',
                         tour=group, 
                         itinerary=itineraries,
                         company=company,
                         current_time=current_time)

@tour_projects.route('/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_tour_group(group_id):
    from ..models.TourProject import TourGroup, TourItinerary
    from flask import request, redirect, url_for, flash, jsonify
    from datetime import datetime
    
    group = TourGroup.query.get_or_404(group_id)
    # 使用数据库排序，按date字段升序排列
    itineraries = TourItinerary.query.filter_by(tour_id=group_id).order_by(TourItinerary.date.asc()).all()
    
    if request.method == 'POST':
        try:
            print(f"收到团信息更新请求，group_id: {group_id}")
            print(f"表单数据: {dict(request.form)}")
            print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
            
            # 检查出发日期和返回日期是否发生变化（在更新之前保存原始值）
            old_departure_date = group.departure_date
            old_return_date = group.return_date
            
            group.title = request.form.get('title')
            # 转换日期格式
            departure_date_str = request.form.get('departure_date')
            return_date_str = request.form.get('return_date')
            
            if departure_date_str:
                group.departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
            if return_date_str:
                group.return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
                
            group.pax = request.form.get('pax')
            group.agency = request.form.get('agency')
            group.operator = request.form.get('operator')
            group.hotel_info = request.form.get('hotel_info')
            group.project_type = request.form.get('project_type')
            group.created_by = request.form.get('created_by')
            group.group_code = request.form.get('group_code')
            group.group_status = request.form.get('group_status')
            group.transport = request.form.get('transport')
            group.meals = request.form.get('meals')
            group.attractions = request.form.get('attractions')
            group.included_items = request.form.get('included_items')
            group.excluded_items = request.form.get('excluded_items')
            group.important_notes = request.form.get('important_notes')
            
            # 保存团信息
            db.session.commit()
            print("团信息更新成功")
            
            # 如果出发日期或返回日期发生变化，自动更新行程安排中的日期
            if (old_departure_date != group.departure_date or old_return_date != group.return_date):
                print(f"检测到日期变化，开始更新行程安排")
                print(f"原出发日期: {old_departure_date}, 新出发日期: {group.departure_date}")
                print(f"原返回日期: {old_return_date}, 新返回日期: {group.return_date}")
                
                # 获取该团的所有行程安排，按日期排序
                itineraries = TourItinerary.query.filter_by(tour_id=group_id).order_by(TourItinerary.date.asc()).all()
                
                if itineraries:
                    # 计算新的日期范围
                    from datetime import timedelta
                    
                    # 更新每个行程的日期
                    for i, itinerary in enumerate(itineraries):
                        # 计算新日期：出发日期 + 天数差
                        new_date = group.departure_date + timedelta(days=i)
                        
                        # 确保新日期不超过返回日期
                        if new_date <= group.return_date:
                            itinerary.date = new_date
                            print(f"更新行程 {itinerary.day_title}: {itinerary.date} -> {new_date}")
                        else:
                            print(f"警告：行程 {itinerary.day_title} 的新日期 {new_date} 超过返回日期 {group.return_date}")
                    
                    # 保存更新后的行程安排
                    db.session.commit()
                    print(f"成功更新了 {len(itineraries)} 个行程安排的日期")
                else:
                    print("该团没有行程安排，无需更新日期")
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '行程团修改成功'})
            else:
                flash('行程团修改成功', 'success')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
        except Exception as e:
            print(f"团信息更新失败: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'行程团修改失败：{str(e)}', 'error')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
    
    # GET请求 - 如果是AJAX请求，返回JSON数据；否则重定向
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 返回团队信息用于编辑
        group_data = {
            'id': group.id,
            'title': group.title,
            'departure_date': group.departure_date.strftime('%Y-%m-%d') if group.departure_date else '',
            'return_date': group.return_date.strftime('%Y-%m-%d') if group.return_date else '',
            'pax': group.pax,
            'agency': group.agency,
            'operator': group.operator,
            'group_code': group.group_code,
            'group_status': group.group_status,
            'hotel_info': group.hotel_info,
            'transport': group.transport,
            'meals': group.meals,
            'attractions': group.attractions,
            'included_items': group.included_items,
            'excluded_items': group.excluded_items,
            'important_notes': group.important_notes
        }
        return jsonify({'success': True, 'group': group_data})
    else:
        # 非AJAX请求重定向到项目编辑页面
        return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))

@tour_projects.route('/group/<int:group_id>/delete', methods=['POST'])
@csrf.exempt
def delete_tour_group(group_id):
    """删除行程团"""
    from flask_wtf.csrf import CSRFError
    
    try:
        print(f"收到删除团请求，group_id: {group_id}")
        print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        group = TourGroup.query.get_or_404(group_id)
        project_id = group.project_id
        
        # 删除团及其关联的行程
        db.session.delete(group)
        db.session.commit()
        
        print("团删除成功")
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '团删除成功'})
        else:
            flash('团删除成功！', 'success')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
            
    except CSRFError as e:
        print(f"CSRF验证失败: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'CSRF验证失败，请刷新页面重试'})
        else:
            flash('CSRF验证失败，请刷新页面重试', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
    except Exception as e:
        print(f"删除团失败: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        else:
            flash(f'删除失败：{str(e)}', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))

# 行程安排管理
@tour_projects.route('/groups/<int:group_id>/itinerary/add', methods=['GET', 'POST'])
@csrf.exempt
def add_itinerary(group_id):
    """添加行程安排"""
    group = TourGroup.query.get_or_404(group_id)
    
    if request.method == 'POST':
        try:
            new_itinerary = TourItinerary(
                tour_id=group_id,
                day_title=request.form.get('day_title'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                content=request.form.get('content')
            )
            db.session.add(new_itinerary)
            db.session.commit()
            flash('行程安排添加成功！', 'success')
            return redirect(url_for('tour_projects.view_tour_group', group_id=group_id))
        except Exception as e:
            flash(f'添加失败：{str(e)}', 'error')
    
    return render_template('projects/TourProjects/add_itinerary.html', group=group)

@tour_projects.route('/itinerary/<int:itinerary_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_itinerary(itinerary_id):
    """编辑行程安排"""
    from flask import jsonify
    from flask_wtf.csrf import CSRFError
    
    itinerary = TourItinerary.query.get_or_404(itinerary_id)
    
    if request.method == 'POST':
        try:
            itinerary.day_title = request.form.get('day_title')
            itinerary.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            itinerary.content = request.form.get('content')
            
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '行程安排更新成功'})
            else:
                flash('行程安排更新成功！', 'success')
                # 重定向到项目编辑页面
                return redirect(url_for('tour_projects.edit_tour_project', project_id=itinerary.tour_group.project_id))
        except CSRFError as e:
            print(f"CSRF验证失败: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'CSRF验证失败，请刷新页面重试'})
            else:
                flash('CSRF验证失败，请刷新页面重试', 'error')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=itinerary.tour_group.project_id))
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'更新失败：{str(e)}', 'error')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=itinerary.tour_group.project_id))
    
    # GET请求 - 如果是AJAX请求，返回JSON数据；否则渲染模板
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 返回行程信息用于编辑
        itinerary_data = {
            'id': itinerary.id,
            'day_title': itinerary.day_title,
            'date': itinerary.date.strftime('%Y-%m-%d') if itinerary.date else '',
            'content': itinerary.content
        }
        return jsonify({'success': True, 'itinerary': itinerary_data})
    else:
        return render_template('projects/TourProjects/edit_itinerary.html', itinerary=itinerary)

@tour_projects.route('/itinerary/<int:itinerary_id>/delete', methods=['POST'])
@csrf.exempt
def delete_itinerary(itinerary_id):
    """删除行程安排"""
    from flask_wtf.csrf import CSRFError
    
    try:
        print(f"收到删除行程请求，itinerary_id: {itinerary_id}")
        print(f"请求头: {dict(request.headers)}")
        print(f"表单数据: {dict(request.form)}")
        print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        itinerary = TourItinerary.query.get_or_404(itinerary_id)
        group_id = itinerary.tour_id
        project_id = itinerary.tour_group.project_id
        print(f"找到行程，group_id: {group_id}, project_id: {project_id}")
        
        db.session.delete(itinerary)
        db.session.commit()
        print("行程删除成功")
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            print("返回AJAX响应")
            return jsonify({'success': True, 'message': '行程安排删除成功'})
        else:
            print("返回重定向响应")
            flash('行程安排删除成功！', 'success')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
    except CSRFError as e:
        print(f"CSRF验证失败: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'CSRF验证失败，请刷新页面重试'})
        else:
            flash('CSRF验证失败，请刷新页面重试', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
    except Exception as e:
        print(f"删除行程时发生错误: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        else:
            flash(f'删除失败：{str(e)}', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))

@tour_projects.route('/edit/<int:project_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_tour_project(project_id):
    """编辑旅游项目页面"""
    project = TourProject.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            # 添加调试信息
            print(f"收到项目更新请求，project_id: {project_id}")
            print(f"表单数据: {dict(request.form)}")
            print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
            
            # 更新项目基本信息
            project.project_name = request.form.get('project_name', '').strip()
            project.project_hid = request.form.get('project_hid', '').strip()
            project.project_type = request.form.get('project_type', '').strip()
            project.contact_person = request.form.get('contact_person', '').strip()
            project.contact_info = request.form.get('contact_info', '').strip()
            project.remarks = request.form.get('remarks', '').strip()
            
            # 处理预算字段
            budget_value = request.form.get('budget', '').strip()
            print(f"预算字段原始值: '{budget_value}'")
            if budget_value:
                try:
                    project.budget = float(budget_value)
                    print(f"预算字段转换成功: {project.budget}")
                except ValueError:
                    project.budget = None
                    print(f"预算字段转换失败，设置为None")
            else:
                project.budget = None
                print(f"预算字段为空，设置为None")
            
            # 保存项目
            db.session.commit()
            print("项目信息保存成功")
            flash('项目信息保存成功！', 'success')
            
            # 如果是AJAX请求，返回JSON响应
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '项目信息保存成功！'})
            
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'保存失败：{str(e)}', 'error')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'保存失败：{str(e)}'})
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
    
    # 获取项目的团信息
    groups = TourGroup.query.filter_by(project_id=project_id).all()
    
    # 为每个团获取行程信息并按日期排序
    for group in groups:
        # 使用数据库排序，按date字段升序排列
        itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
        group.itineraries = itineraries

    # 配套价格预算：获取最近的预算单用于页面快速查看
    try:
        from ..models.PackageBudget import BudgetHeader
        recent_budgets = BudgetHeader.query.order_by(BudgetHeader.created_at.desc()).limit(10).all()
    except Exception:
        recent_budgets = []
    
    return render_template('projects/TourProjects/tour_project_edit.html',
                         project=project, 
                         groups=groups,
                         recent_budgets=recent_budgets)

@tour_projects.route('/detail/<int:project_id>', methods=['GET'])
def project_details(project_id):
    """项目详细页面"""
    project = TourProject.query.get_or_404(project_id)
    
    # 获取项目的团信息
    groups = TourGroup.query.filter_by(project_id=project_id).all()
    
    # 为每个团获取行程信息，使用数据库排序
    for group in groups:
        # 使用数据库排序，按date字段升序排列
        itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
        group.itineraries = itineraries
    
    return render_template('projects/TourProjects/tour_project_detail.html',
                         project=project, 
                         groups=groups)

@tour_projects.route('/itinerary/create/<int:group_id>', methods=['GET', 'POST'])
@csrf.exempt
def create_itinerary(group_id):
    from ..models.TourProject import TourItinerary, TourGroup
    from flask import request, redirect, url_for, render_template, flash, jsonify
    from flask_wtf.csrf import CSRFError
    
    group = TourGroup.query.get_or_404(group_id)
    if request.method == 'POST':
        try:
            # 添加调试信息
            print(f"收到创建行程请求，group_id: {group_id}")
            print(f"请求头: {dict(request.headers)}")
            print(f"表单数据: {dict(request.form)}")
            print(f"是否是AJAX请求: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
            
            new_itinerary = TourItinerary(
                tour_id=group_id,
                day_title=request.form.get('day_title'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                content=request.form.get('content')
            )
            db.session.add(new_itinerary)
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                print("返回AJAX响应")
                return jsonify({'success': True, 'message': '行程添加成功'})
            else:
                print("返回重定向响应")
                flash('行程添加成功', 'success')
                # 重定向到项目编辑页面而不是团编辑页面
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
        except CSRFError as e:
            print(f"CSRF验证失败: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'CSRF验证失败，请刷新页面重试'})
            else:
                flash('CSRF验证失败，请刷新页面重试', 'error')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
        except Exception as e:
            print(f"创建行程时发生错误: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'行程添加失败：{str(e)}', 'error')
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
    
    return render_template('projects/TourProjects/create_itinerary.html', group=group)
