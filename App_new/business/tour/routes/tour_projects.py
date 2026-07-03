from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from App_new.exts import db, csrf
from App_new.business.tour.models.TourProject import TourGroup, TourItinerary, TourProject, TourProjectAttachment
from flask import send_file
from App_new.business.tour.models.Packagemodels import CompanyInfo
from datetime import datetime
import os
import sys
import subprocess
import urllib.parse
import html
import logging
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
from werkzeug.utils import secure_filename
import uuid

# 创建蓝图
tour_projects = Blueprint('tour_projects', __name__)

def create_folder(base_path, folder_name):
    """创建文件夹的辅助函数"""
    folder_path = os.path.join(base_path, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def save_uploaded_image(file, upload_folder):
    """保存上传的图片文件"""
    if file and file.filename:
        # 生成唯一的文件名
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # 确保上传目录存在
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # 保存文件
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # 返回相对于static目录的路径
        return f"itinerary_images/{unique_filename}"
    return None

@tour_projects.route('/create', methods=['GET', 'POST'])
@csrf.exempt
def create_tour_project():
    """创建旅游项目页面 - 同时创建项目和团队"""
    if request.method == 'POST':
        try:
            print("=== 收到POST请求 ===")
            print(f"表单数据: {dict(request.form)}")
            print(f"请求头: {dict(request.headers)}")
            
            # 从前端表单中获取项目信息
            project_name = request.form.get('projectName', '').strip()
            project_hid = request.form.get('projectHID', '').strip()
            project_type = request.form.get('projectType', '').strip()
            budget_value = request.form.get('budget', '').strip()
            project_status = request.form.get('projectStatus', '').strip()
            contact_person = request.form.get('contactPerson', '').strip()
            contact_info = request.form.get('contactInfo', '').strip()
            remarks = request.form.get('remarks', '').strip()
            
            # 从前端表单中获取团队信息
            group_title = request.form.get('groupTitle', '').strip()
            departure_date = request.form.get('departureDate', '').strip()
            return_date = request.form.get('returnDate', '').strip()
            pax = request.form.get('pax', '1').strip()
            agency = request.form.get('agency', '').strip()
            operator = request.form.get('operator', '').strip()
            group_code = request.form.get('groupCode', '').strip()
            group_status = request.form.get('groupStatus', '计划中').strip()
            
            # 详细说明字段
            included_items = request.form.get('includedItems', '').strip()
            excluded_items = request.form.get('excludedItems', '').strip()
            important_notes = request.form.get('importantNotes', '').strip()
            
            creation_date = datetime.now().date()

            print(f"解析后的数据:")
            print(f"  project_name: '{project_name}'")
            print(f"  departure_date: '{departure_date}'")
            print(f"  return_date: '{return_date}'")
            print(f"  pax: '{pax}'")

            # 验证必填字段是否完整
            required_fields = [project_name, departure_date, return_date, project_status, contact_person, pax]
            print(f"必填字段检查: {required_fields}")
            print(f"所有字段都有值: {all(required_fields)}")
            
            if not all(required_fields):
                missing_fields = []
                if not project_name: missing_fields.append('项目名称')
                if not departure_date: missing_fields.append('出发日期')
                if not return_date: missing_fields.append('返回日期')
                if not project_status: missing_fields.append('项目状态')
                if not contact_person: missing_fields.append('联系人')
                if not pax: missing_fields.append('人数')
                
                error_msg = f'缺少必填字段: {", ".join(missing_fields)}'
                print(f"验证失败: {error_msg}")
                flash(error_msg, 'error')
                return redirect(url_for('tour_projects.create_tour_project'))

            # 验证日期格式
            try:
                formatted_departure_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
                formatted_return_date = datetime.strptime(return_date, "%Y-%m-%d").date()
                print(f"日期解析成功: 出发 {formatted_departure_date}, 返回 {formatted_return_date}")
                
                # 验证返回日期不早于出发日期
                if formatted_return_date < formatted_departure_date:
                    flash('返回日期不能早于出发日期', 'error')
                    return redirect(url_for('tour_projects.create_tour_project'))
                    
            except ValueError as e:
                print(f"日期解析失败: {e}")
                flash('日期格式无效，请选择有效的日期', 'error')
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
            
            # 处理人数字段
            try:
                pax_int = int(pax)
            except ValueError:
                pax_int = 1
            
            # 创建 TourProject 实例
            new_project = TourProject(
                project_name=project_name,
                project_hid=project_hid if project_hid else None,
                project_type=project_type,
                budget=budget,
                project_status=project_status,
                folder_name=folder_name,
                contact_person=contact_person,
                contact_info=contact_info,
                remarks=remarks,
                departure_date=formatted_departure_date
            )

            print("TourProject实例创建成功")

            # 将新项目添加到数据库会话
            db.session.add(new_project)
            db.session.flush()  # 获取项目ID
            
            print(f"项目ID: {new_project.id}")
            
            # 创建 TourGroup 实例
            new_group = TourGroup(
                title=group_title if group_title else project_name,  # 如果团队名称为空，使用项目名称
                departure_date=formatted_departure_date,
                return_date=formatted_return_date,
                pax=pax_int,
                agency=agency if agency else None,
                operator=operator if operator else None,
                group_code=group_code if group_code else None,
                group_status=group_status,
                included_items=included_items if included_items else None,
                excluded_items=excluded_items if excluded_items else None,
                important_notes=important_notes if important_notes else None,
                project_id=new_project.id
            )
            
            print("TourGroup实例创建成功")
            
            db.session.add(new_group)

            # 提交到数据库
            db.session.commit()
            print("数据库提交成功")

            flash('旅游项目和团队创建成功！', 'success')
            # 直接跳转到编辑页面，方便用户继续添加行程
            return redirect(url_for('tour_projects.edit_tour_project', project_id=new_project.id))

        except Exception as e:
            db.session.rollback()
            print(f"发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            logging.error(f"数据库操作失败: {e}")
            flash('创建旅游项目失败，请稍后重试', 'error')
            return redirect(url_for('tour_projects.create_tour_project'))

    # GET请求：渲染创建页面
    return render_template('business/tour/package/TourProjects/tour_project_create.html')

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

    # 获取所有项目的 HID，构建 HID 到 ProjectHeader ID 的映射
    from App_new.business.projects.models.project import ProjectHeader
    hid_list = [p.project_hid for p in tour_projects if p.project_hid]
    hid_to_project_id = {}
    if hid_list:
        headers = ProjectHeader.query.filter(ProjectHeader.hid.in_(hid_list)).all()
        hid_to_project_id = {h.hid: h.id for h in headers}

    return render_template('business/tour/package/TourProjects/tour_project_list.html',
                         projects=tour_projects,
                         pagination=pagination,
                         travel_status=travel_status, 
                         sort_by=sort_by, 
                         order=order,
                         hid_to_project_id=hid_to_project_id)

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

@tour_projects.route('/copy/<int:project_id>', methods=['POST'])
@csrf.exempt
def copy_tour_project(project_id):
    """复制旅游项目及其关联数据"""
    try:
        # 获取原项目
        original_project = TourProject.query.get_or_404(project_id)

        # 生成新的项目名称
        new_project_name = f"{original_project.project_name} (副本)"

        # 生成新的文件夹名称
        from ....config import Config
        tour_project_path = Config.TOUR_PROJECTS_PATH
        creation_date = datetime.now().date()

        if original_project.project_hid:
            folder_name = f"{creation_date}_{original_project.project_hid}_{new_project_name}"
        else:
            folder_name = f"{creation_date}_{new_project_name}"

        # 创建文件夹
        create_folder(tour_project_path, folder_name)

        # 创建新项目
        new_project = TourProject(
            project_name=new_project_name,
            project_hid=original_project.project_hid,
            project_type=original_project.project_type,
            budget=original_project.budget,
            project_status='处理中',  # 新复制的项目默认为处理中状态
            folder_name=folder_name,
            contact_person=original_project.contact_person,
            contact_info=original_project.contact_info,
            remarks=original_project.remarks,
            departure_date=original_project.departure_date
        )
        # 复制货币单位（__init__不接受此参数，需单独设置）
        new_project.currency = original_project.currency

        db.session.add(new_project)
        db.session.flush()  # 获取新项目ID

        # 复制所有关联的团组（记录 旧团组ID→新团组ID，供价格预算的 group_id 重映射）
        group_id_map = {}
        original_groups = TourGroup.query.filter_by(project_id=project_id).all()
        for original_group in original_groups:
            new_group = TourGroup(
                title=original_group.title,
                group_code=original_group.group_code,
                group_status=original_group.group_status,
                project_type=original_group.project_type,
                departure_date=original_group.departure_date,
                return_date=original_group.return_date,
                pax=original_group.pax,
                budget_per_person=original_group.budget_per_person,
                adult_price=original_group.adult_price,
                child_price=original_group.child_price,
                agency=original_group.agency,
                operator=original_group.operator,
                included_items=original_group.included_items,
                excluded_items=original_group.excluded_items,
                important_notes=original_group.important_notes,
                project_id=new_project.id
            )

            db.session.add(new_group)
            db.session.flush()  # 获取新团组ID
            group_id_map[original_group.id] = new_group.id

            # 复制该团组的所有行程安排
            original_itineraries = TourItinerary.query.filter_by(tour_id=original_group.id).all()
            for original_itinerary in original_itineraries:
                new_itinerary = TourItinerary(
                    tour_id=new_group.id,
                    day_title=original_itinerary.day_title,
                    date=original_itinerary.date,
                    content=original_itinerary.content,
                    image1=original_itinerary.image1,  # 图片路径共享（不复制物理文件）
                    image2=original_itinerary.image2,
                    image3=original_itinerary.image3
                )
                db.session.add(new_itinerary)

        # 复制关联的价格预算单（含明细），group_id 重映射到新团组
        from App_new.business.tour.models.PackageBudget import BudgetHeader, BudgetItem
        original_budgets = BudgetHeader.query.filter_by(project_id=project_id).all()
        for ob in original_budgets:
            new_budget = BudgetHeader(
                package_name=ob.package_name,
                adult_count=ob.adult_count,
                child_count=ob.child_count,
                currency=ob.currency,
                target_currency=ob.target_currency,
                exchange_rate=ob.exchange_rate,
                status=ob.status,
                is_template=ob.is_template,
                remarks=ob.remarks,
                created_by=ob.created_by,
                created_at=datetime.utcnow(),
                project_id=new_project.id,
                group_id=group_id_map.get(ob.group_id),  # 旧团组→新团组
            )
            db.session.add(new_budget)
            db.session.flush()  # 获取新预算单ID

            for oi in ob.items:
                db.session.add(BudgetItem(
                    header_id=new_budget.id,
                    category=oi.category,
                    item_name=oi.item_name,
                    item_details=oi.item_details,
                    pricing_method=oi.pricing_method,
                    item_unit_price=oi.item_unit_price,
                    item_quantity=oi.item_quantity,
                    adult_price=oi.adult_price,
                    child_price=oi.child_price,
                    count_adult_apply=oi.count_adult_apply,
                    count_child_apply=oi.count_child_apply,
                    adult_count_override=oi.adult_count_override,
                    child_count_override=oi.child_count_override,
                    total_override=oi.total_override,
                    sort_order=oi.sort_order,
                    tax_rate=oi.tax_rate,
                    tax_amount=oi.tax_amount,
                    is_optional=oi.is_optional,
                    remarks=oi.remarks,
                ))

        # 提交所有更改
        db.session.commit()

        # 返回响应
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': '项目复制成功！',
                'new_project_id': new_project.id,
                'redirect_url': url_for('tour_projects.edit_tour_project', project_id=new_project.id)
            })
        else:
            flash('项目复制成功！', 'success')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=new_project.id))

    except Exception as e:
        db.session.rollback()
        print(f"复制项目失败: {str(e)}")
        import traceback
        traceback.print_exc()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'复制失败：{str(e)}'}), 500
        else:
            flash(f'复制失败：{str(e)}', 'error')
            return redirect(url_for('tour_projects.manage_tour_projects'))


@tour_projects.route('/delete/<int:project_id>', methods=['POST'])
@csrf.exempt
def delete_tour_project(project_id):
    """删除旅游项目"""
    try:
        project = TourProject.query.get(project_id)
        if not project:
            return jsonify({"success": False, "message": "项目不存在"}), 404

        # 先删除关联的行程数据
        groups = TourGroup.query.filter_by(project_id=project_id).all()
        for group in groups:
            # 删除团组下的所有行程
            TourItinerary.query.filter_by(tour_id=group.id).delete()
            # 删除团组
            db.session.delete(group)
        
        # 最后删除项目
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True, "message": "项目及关联数据删除成功"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"删除项目失败: {str(e)}")
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
    return render_template('business/tour/package/TourProjects/tour_groups.html', groups=groups)

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
            project_id=project_id,
            created_by=request.form.get('created_by'),
            group_code=request.form.get('group_code'),
            group_status=request.form.get('group_status'),
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
    return render_template('business/tour/package/TourProjects/tour_project_print_confirmation.html',
                         tour=group, 
                         itinerary=itineraries,
                         company=company,
                         current_time=current_time)

@tour_projects.route('/groups/<int:group_id>/itinerary', methods=['GET'])
def view_tour_itinerary(group_id):
    """查看行程单（仅包含每日行程安排和价格信息）"""
    group = None
    try:
        # 使用 joinload 或 joinedload 预加载 project 关系，避免懒加载问题
        from sqlalchemy.orm import joinedload
        group = TourGroup.query.options(joinedload(TourGroup.project)).get_or_404(group_id)
        print(f"✅ 找到团组: {group_id}, 标题: {group.title}")
        
        itineraries = TourItinerary.query.filter_by(tour_id=group_id).order_by(TourItinerary.date.asc()).all()
        print(f"✅ 找到 {len(itineraries)} 条行程")
        
        company = CompanyInfo.query.first()
        print(f"✅ 公司信息: {company.company_name if company else 'None'}")
        
        current_time = datetime.now()

        # 验证 project 关系是否正常
        if group.project_id:
            if group.project is None:
                print(f"⚠️ 警告: 团组 {group_id} 的 project_id={group.project_id} 但对应的项目不存在")
            else:
                print(f"✅ 项目关系已加载: {group.project.project_name}")

        # 价格取自项目的价格预算单：优先绑定本团组的，否则取项目最新一张
        project_budget = None
        if group.project_id:
            from App_new.business.tour.models.PackageBudget import BudgetHeader
            project_budget = BudgetHeader.query.filter_by(
                    project_id=group.project_id, group_id=group.id)\
                .order_by(BudgetHeader.created_at.desc()).first() \
                or BudgetHeader.query.filter_by(project_id=group.project_id)\
                .order_by(BudgetHeader.created_at.desc()).first()

        return render_template('business/tour/package/TourProjects/tour_project_print_itinerary.html',
                             tour=group,
                             itinerary=itineraries,
                             company=company,
                             current_time=current_time,
                             project_budget=project_budget)
    except Exception as e:
        import traceback
        error_msg = f"❌ 渲染行程单时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        flash(f'加载行程单失败：{str(e)}', 'error')
        try:
            if group and group.project_id:
                return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))
        except Exception as redirect_error:
            print(f"⚠️ 重定向失败: {str(redirect_error)}")
        # 如果无法重定向，返回错误信息
        from flask import render_template_string
        return render_template_string('''
        <html>
        <head><title>错误</title></head>
        <body>
            <h1>加载行程单失败</h1>
            <p>{{ error }}</p>
            <a href="javascript:history.back()">返回</a>
        </body>
        </html>
        ''', error=str(e)), 500

@tour_projects.route('/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_tour_group(group_id):
    from App_new.business.tour.models.TourProject import TourGroup, TourItinerary
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
            sync_warning = None  # 人数同步到预算单时的提示（多团组未指定等）
            
            group.title = request.form.get('title')
            # 转换日期格式
            departure_date_str = request.form.get('departure_date')
            return_date_str = request.form.get('return_date')
            
            if departure_date_str:
                group.departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
            if return_date_str:
                group.return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
                
            # 大人/小孩 → 自动汇总总人数 pax
            # 两者皆空：保护历史数据，adult/child/pax 全不动
            adult_raw = (request.form.get('adult_count') or '').strip()
            child_raw = (request.form.get('child_count') or '').strip()
            if adult_raw == '' and child_raw == '':
                pass
            else:
                adult_n = int(adult_raw) if adult_raw else 0
                child_n = int(child_raw) if child_raw else 0
                group.adult_count = adult_n
                group.child_count = child_n
                group.pax = adult_n + child_n
                # 双向同步：团组人数 → 预算单（按团组精确匹配，多团组不拉平；允许成人=0）
                if group.project_id:
                    from App_new.business.tour.routes.package_budget import sync_group_counts_to_budgets
                    _synced, _skipped_multi = sync_group_counts_to_budgets(
                        group.project_id, group.id, adult_n, child_n)
                    if _skipped_multi:
                        sync_warning = '项目有多个团组且预算单未指定对应团组，人数未自动同步到预算单'
            group.agency = request.form.get('agency')
            group.operator = request.form.get('operator')
            group.project_type = request.form.get('project_type')
            group.created_by = request.form.get('created_by')
            group.group_code = request.form.get('group_code')
            group.group_status = request.form.get('group_status')
            # 处理人均预算
            budget_per_person_str = request.form.get('budget_per_person', '').strip()
            group.budget_per_person = float(budget_per_person_str) if budget_per_person_str else None
            # 注：价格已改为自动取自项目的价格预算单（BudgetHeader），团队弹窗不再维护价格
            # 套餐说明已迁出本弹窗、改由独立区块保存；
            # 仅当表单确实带了这些字段时才更新，避免编辑团队时被清空
            if 'included_items' in request.form:
                group.included_items = request.form.get('included_items')
            if 'excluded_items' in request.form:
                group.excluded_items = request.form.get('excluded_items')
            if 'important_notes' in request.form:
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
                msg = '行程团修改成功' + (f'（{sync_warning}）' if sync_warning else '')
                return jsonify({'success': True, 'message': msg, 'warning': sync_warning})
            else:
                flash('行程团修改成功', 'success')
                if sync_warning:
                    flash(sync_warning, 'warning')
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
            'adult_count': group.adult_count,
            'child_count': group.child_count,
            'agency': group.agency,
            'operator': group.operator,
            'group_code': group.group_code,
            'group_status': group.group_status,
            'budget_per_person': group.budget_per_person,
            'adult_price': group.adult_price,
            'child_price': group.child_price,
            'included_items': group.included_items,
            'excluded_items': group.excluded_items,
            'important_notes': group.important_notes
        }
        return jsonify({'success': True, 'group': group_data})
    else:
        # 非AJAX请求重定向到项目编辑页面
        return redirect(url_for('tour_projects.edit_tour_project', project_id=group.project_id))

@tour_projects.route('/groups/<int:group_id>/package-info', methods=['POST'])
@csrf.exempt
def edit_group_package_info(group_id):
    """只更新团组的套餐说明三字段（包含/不包含/注意事项）

    独立于"编辑团队"弹窗，由每日行程之后的独立区块调用。
    接收 JSON，空字符串存为 None（与原弹窗逻辑一致：空即清除）。
    """
    from App_new.business.tour.models.TourProject import TourGroup

    group = TourGroup.query.get_or_404(group_id)
    data = request.get_json(silent=True) or {}

    try:
        def norm(v):
            v = (v or '').strip()
            return v if v else None

        group.included_items = norm(data.get('included_items'))
        group.excluded_items = norm(data.get('excluded_items'))
        group.important_notes = norm(data.get('important_notes'))
        db.session.commit()
        return jsonify({'success': True, 'message': '套餐说明已保存'})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


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
    
    return render_template('business/tour/package/TourProjects/add_itinerary.html', group=group)

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
            
            # 处理删除标记（仅清除引用，不删除物理文件，物理文件通过图片库管理删除）
            remove_image1 = request.form.get('remove_image1') == '1'
            remove_image2 = request.form.get('remove_image2') == '1'
            remove_image3 = request.form.get('remove_image3') == '1'

            if remove_image1 and itinerary.image1:
                itinerary.image1 = None
            if remove_image2 and itinerary.image2:
                itinerary.image2 = None
            if remove_image3 and itinerary.image3:
                itinerary.image3 = None

            # 处理图片上传
            upload_folder = os.path.join('App_new', 'static', 'itinerary_images')

            # 处理图片1：图库路径优先于文件上传
            image1_lib = (request.form.get('image1_library_path') or '').strip()
            if image1_lib:
                itinerary.image1 = image1_lib
            elif 'image1' in request.files:
                image1_file = request.files['image1']
                if image1_file and image1_file.filename:
                    image1_path = save_uploaded_image(image1_file, upload_folder)
                    if image1_path:
                        itinerary.image1 = image1_path

            # 处理图片2
            image2_lib = (request.form.get('image2_library_path') or '').strip()
            if image2_lib:
                itinerary.image2 = image2_lib
            elif 'image2' in request.files:
                image2_file = request.files['image2']
                if image2_file and image2_file.filename:
                    image2_path = save_uploaded_image(image2_file, upload_folder)
                    if image2_path:
                        itinerary.image2 = image2_path

            # 处理图片3
            image3_lib = (request.form.get('image3_library_path') or '').strip()
            if image3_lib:
                itinerary.image3 = image3_lib
            elif 'image3' in request.files:
                image3_file = request.files['image3']
                if image3_file and image3_file.filename:
                    image3_path = save_uploaded_image(image3_file, upload_folder)
                    if image3_path:
                        itinerary.image3 = image3_path

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
            'content': itinerary.content,
            'image1': itinerary.image1,
            'image2': itinerary.image2,
            'image3': itinerary.image3
        }
        return jsonify({'success': True, 'itinerary': itinerary_data})
    else:
        return render_template('business/tour/package/TourProjects/edit_itinerary.html', itinerary=itinerary)

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

@tour_projects.route('/itinerary/clear/<int:group_id>', methods=['POST'])
@csrf.exempt
def clear_group_itineraries(group_id):
    """清空指定团队的所有行程安排（用于自动生成前的覆盖操作）"""
    group = TourGroup.query.get(group_id)
    if not group:
        return jsonify({'success': False, 'message': f'团队不存在 (id={group_id})'}), 404
    try:
        deleted_count = TourItinerary.query.filter_by(tour_id=group_id).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'deleted_count': deleted_count, 'group_id': group_id})
    except Exception as e:
        db.session.rollback()
        print(f"清空团队行程时发生错误: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
            project.project_hid = request.form.get('project_hid', '').strip() or None
            project.project_type = request.form.get('project_type', '').strip() or None
            project.project_status = request.form.get('project_status', '').strip() or None
            project.contact_person = request.form.get('contact_person', '').strip() or ''
            project.contact_info = request.form.get('contact_info', '').strip() or ''
            project.remarks = request.form.get('remarks', '').strip() or None

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
    
    try:
        # 获取项目的团信息
        groups = TourGroup.query.filter_by(project_id=project_id).all()
        print(f"✅ 找到 {len(groups)} 个团组")
        
        # 为每个团获取行程信息并按日期排序
        for group in groups:
            try:
                # 使用数据库排序，按date字段升序排列
                itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
                group.itineraries = itineraries
                print(f"✅ 团组 {group.id} 有 {len(itineraries)} 条行程")
            except Exception as e:
                print(f"⚠️ 获取团组 {group.id} 的行程失败: {str(e)}")
                group.itineraries = []

        # 配套价格预算：获取最近的预算单用于页面快速查看
        # project_budget：本项目最新预算单，用于"价格预算"按钮直达详情页
        try:
            from App_new.business.tour.models.PackageBudget import BudgetHeader
            recent_budgets = BudgetHeader.query.order_by(BudgetHeader.created_at.desc()).limit(10).all()
            project_budget = BudgetHeader.query.filter_by(project_id=project_id)\
                .order_by(BudgetHeader.created_at.desc()).first()
            print(f"✅ 找到 {len(recent_budgets)} 个预算单，本项目预算: {project_budget.id if project_budget else '无'}")
        except Exception as e:
            print(f"⚠️ 获取预算单失败: {str(e)}")
            recent_budgets = []
            project_budget = None
        
        # 获取项目附件
        try:
            attachments = TourProjectAttachment.query.filter_by(project_id=project_id).order_by(TourProjectAttachment.created_at.desc()).all()
            print(f"✅ 找到 {len(attachments)} 个附件")
        except Exception as e:
            print(f"⚠️ 获取附件失败: {str(e)}")
            attachments = []
        
        return render_template('business/tour/package/TourProjects/tour_project_edit.html',
                             project=project, 
                             groups=groups,
                             recent_budgets=recent_budgets,
                             project_budget=project_budget,
                             attachments=attachments)
    except Exception as e:
        import traceback
        error_msg = f"❌ 渲染项目编辑页面时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        flash(f'加载项目编辑页面失败：{str(e)}', 'error')
        # 尝试重定向到项目详情页
        try:
            return redirect(url_for('tour_projects.project_details', project_id=project_id))
        except:
            from flask import render_template_string
            return render_template_string('''
            <html>
            <head><title>错误</title></head>
            <body>
                <h1>加载项目编辑页面失败</h1>
                <p>{{ error }}</p>
                <a href="javascript:history.back()">返回</a>
            </body>
            </html>
            ''', error=str(e)), 500

@tour_projects.route('/<int:project_id>/create-linked-header', methods=['POST'])
@csrf.exempt
def create_linked_header(project_id):
    """为旅游项目自动创建主系统 HID 项目（ProjectHeader），并回写 project_hid

    - 已关联（project_hid 对应到已存在的 ProjectHeader）则幂等返回该项目，不重复创建
    - 否则按旅游项目信息生成新的 ProjectHeader，自动生成 HID
    """
    from App_new.business.projects.models.project import ProjectHeader
    from flask_login import current_user
    from sqlalchemy.exc import IntegrityError

    tour = TourProject.query.get_or_404(project_id)

    try:
        # 幂等：已有 project_hid 且能在主系统找到对应 header，直接返回
        # 注意：只有 header 真实存在才算已关联，避免脏的 project_hid 返回 404 链接
        if tour.project_hid:
            existing = ProjectHeader.query.filter_by(hid=tour.project_hid.strip()).first()
            if existing:
                return jsonify({
                    'success': True,
                    'already_linked': True,
                    'hid': existing.hid,
                    'header_id': existing.id,
                    'detail_url': url_for('business_projects.detail.project_detail', project_id=existing.id),
                    'message': f'该旅游项目已关联主项目 {existing.hid}，未重复创建'
                })
            # project_hid 有值但 header 不存在 → 视为脏数据，继续走新建覆盖

        staff_id = current_user.id if getattr(current_user, 'is_authenticated', False) else None

        # generate_hid 是"读 max 再 +1"，并发/双击会撞 hid UNIQUE 约束。
        # 用重试 + IntegrityError 兜底，保证一次请求最终拿到唯一 hid 且原子提交。
        last_err = None
        for _attempt in range(5):
            header = ProjectHeader(
                hid=ProjectHeader.generate_hid(),
                desc=tour.project_name,
                company_id=None,                       # 旅游项目默认个人客户
                contact=tour.contact_person,
                staff_id=staff_id,
                currency=tour.currency or 'SGD',
                type=tour.project_type or 'Tour',
                status='active',
                remarks=tour.remarks
            )
            # staff_name 由模型事件自动同步，用它兜底 leader/operator/salesperson
            header.leader_name = tour.contact_person or header.staff_name
            header.operator_ids = str(staff_id) if staff_id else None
            header.operator_names = header.staff_name
            header.salesperson_ids = str(staff_id) if staff_id else None
            header.salesperson_names = header.staff_name

            db.session.add(header)
            try:
                db.session.flush()          # 触发 hid UNIQUE 检查，拿到 id
                tour.project_hid = header.hid
                db.session.commit()         # header 与 tour 关联在同一事务里原子提交
                return jsonify({
                    'success': True,
                    'already_linked': False,
                    'hid': header.hid,
                    'header_id': header.id,
                    'detail_url': url_for('business_projects.detail.project_detail', project_id=header.id),
                    'message': f'已创建主项目 {header.hid} 并关联'
                })
            except IntegrityError as ie:
                # hid 撞车（并发），回滚后重新生成重试
                db.session.rollback()
                last_err = ie
                tour = TourProject.query.get_or_404(project_id)
                # 重试前再查一次：可能并发的另一请求已建好并回写
                if tour.project_hid:
                    ex = ProjectHeader.query.filter_by(hid=tour.project_hid.strip()).first()
                    if ex:
                        return jsonify({
                            'success': True,
                            'already_linked': True,
                            'hid': ex.hid,
                            'header_id': ex.id,
                            'detail_url': url_for('business_projects.detail.project_detail', project_id=ex.id),
                            'message': f'该旅游项目已关联主项目 {ex.hid}，未重复创建'
                        })
                continue

        raise last_err or RuntimeError('生成 HID 多次重试仍失败')

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'创建失败：{str(e)}'}), 500


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
    
    return render_template('business/tour/package/TourProjects/tour_project_detail.html',
                         project=project, 
                         groups=groups)

@tour_projects.route('/itinerary/create/<int:group_id>', methods=['GET', 'POST'])
@csrf.exempt
def create_itinerary(group_id):
    from App_new.business.tour.models.TourProject import TourItinerary, TourGroup
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
            db.session.flush()  # 获取新创建的ID
            
            # 处理图片上传
            upload_folder = os.path.join('App_new', 'static', 'itinerary_images')

            # 处理图片1：图库路径优先于文件上传
            image1_lib = (request.form.get('image1_library_path') or '').strip()
            if image1_lib:
                new_itinerary.image1 = image1_lib
            elif 'image1' in request.files:
                image1_file = request.files['image1']
                if image1_file and image1_file.filename:
                    image1_path = save_uploaded_image(image1_file, upload_folder)
                    if image1_path:
                        new_itinerary.image1 = image1_path

            # 处理图片2
            image2_lib = (request.form.get('image2_library_path') or '').strip()
            if image2_lib:
                new_itinerary.image2 = image2_lib
            elif 'image2' in request.files:
                image2_file = request.files['image2']
                if image2_file and image2_file.filename:
                    image2_path = save_uploaded_image(image2_file, upload_folder)
                    if image2_path:
                        new_itinerary.image2 = image2_path

            # 处理图片3
            image3_lib = (request.form.get('image3_library_path') or '').strip()
            if image3_lib:
                new_itinerary.image3 = image3_lib
            elif 'image3' in request.files:
                image3_file = request.files['image3']
                if image3_file and image3_file.filename:
                    image3_path = save_uploaded_image(image3_file, upload_folder)
                    if image3_path:
                        new_itinerary.image3 = image3_path
            
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
    
    return render_template('business/tour/package/TourProjects/create_itinerary.html', group=group)


# ========== 附件管理路由 ==========

def save_attachment_file(file, project_id):
    """保存上传的附件文件"""
    if file and file.filename:
        # 生成唯一的文件名
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

        # 使用 Flask 的 static_folder 获取正确的绝对路径
        upload_folder = os.path.join(current_app.static_folder, 'project_attachments', str(project_id))
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # 保存文件（使用绝对路径）
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 存储相对于 static 目录的路径，便于跨环境使用
        relative_path = os.path.join('project_attachments', str(project_id), unique_filename)

        return {
            'original_filename': file.filename,
            'stored_filename': unique_filename,
            'file_path': relative_path,  # 存储相对路径
            'file_size': file_size,
            'file_type': file.content_type
        }
    return None


@tour_projects.route('/project/<int:project_id>/attachments', methods=['GET'])
def list_attachments(project_id):
    """获取项目附件列表"""
    project = TourProject.query.get_or_404(project_id)
    attachments = TourProjectAttachment.query.filter_by(project_id=project_id).order_by(TourProjectAttachment.created_at.desc()).all()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        attachments_data = [{
            'id': a.id,
            'filename': a.filename,
            'file_size': a.file_size_display,
            'file_type': a.file_type,
            'description': a.description,
            'icon_class': a.icon_class,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else ''
        } for a in attachments]
        return jsonify({'success': True, 'attachments': attachments_data})
    
    return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))


@tour_projects.route('/project/<int:project_id>/attachments/upload', methods=['POST'])
@csrf.exempt
def upload_attachment(project_id):
    """上传项目附件"""
    try:
        project = TourProject.query.get_or_404(project_id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        # 保存文件
        file_info = save_attachment_file(file, project_id)
        if not file_info:
            return jsonify({'success': False, 'message': '文件保存失败'}), 500
        
        # 创建附件记录
        attachment = TourProjectAttachment(
            project_id=project_id,
            filename=file_info['original_filename'],
            stored_filename=file_info['stored_filename'],
            file_path=file_info['file_path'],
            file_size=file_info['file_size'],
            file_type=file_info['file_type'],
            description=request.form.get('description', '')
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '文件上传成功',
            'attachment': {
                'id': attachment.id,
                'filename': attachment.filename,
                'file_size': attachment.file_size_display,
                'icon_class': attachment.icon_class,
                'created_at': attachment.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"上传附件失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


def get_attachment_full_path(attachment):
    """获取附件的完整路径，兼容新旧两种路径格式"""
    stored_path = attachment.file_path

    # 新格式：相对路径 (project_attachments/69/xxx.docx)
    file_path = os.path.join(current_app.static_folder, stored_path)
    if os.path.exists(file_path):
        return file_path

    # 旧格式：包含 App_new 前缀 (App_new/static/project_attachments/69/xxx.docx)
    # 尝试移除多余的前缀
    if stored_path.startswith('App_new/static/') or stored_path.startswith('App_new\\static\\'):
        relative_path = stored_path.replace('App_new/static/', '').replace('App_new\\static\\', '')
        file_path = os.path.join(current_app.static_folder, relative_path)
        if os.path.exists(file_path):
            return file_path

    # 尝试作为绝对路径直接访问
    if os.path.exists(stored_path):
        return stored_path

    return None


@tour_projects.route('/attachments/<int:attachment_id>/download', methods=['GET'])
def download_attachment(attachment_id):
    """下载附件"""
    try:
        attachment = TourProjectAttachment.query.get_or_404(attachment_id)

        # 获取完整的文件路径（兼容新旧格式）
        file_path = get_attachment_full_path(attachment)

        if not file_path:
            flash('文件不存在', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=attachment.project_id))

        return send_file(
            file_path,
            as_attachment=True,
            download_name=attachment.filename
        )

    except Exception as e:
        print(f"下载附件失败: {str(e)}")
        flash(f'下载失败：{str(e)}', 'error')
        return redirect(url_for('tour_projects.edit_tour_project', project_id=attachment.project_id))


@tour_projects.route('/attachments/<int:attachment_id>/view', methods=['GET'])
def view_attachment(attachment_id):
    """在线查看附件（主要用于PDF和图片）"""
    try:
        attachment = TourProjectAttachment.query.get_or_404(attachment_id)

        # 获取完整的文件路径（兼容新旧格式）
        file_path = get_attachment_full_path(attachment)

        if not file_path:
            return jsonify({'success': False, 'message': '文件不存在'}), 404

        return send_file(
            file_path,
            as_attachment=False,
            download_name=attachment.filename
        )

    except Exception as e:
        print(f"查看附件失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@tour_projects.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
@csrf.exempt
def delete_attachment(attachment_id):
    """删除附件"""
    try:
        attachment = TourProjectAttachment.query.get_or_404(attachment_id)
        project_id = attachment.project_id

        # 获取完整的文件路径（兼容新旧格式）
        file_path = get_attachment_full_path(attachment)

        # 删除物理文件
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # 删除数据库记录
        db.session.delete(attachment)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '附件删除成功'})
        else:
            flash('附件删除成功', 'success')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
            
    except Exception as e:
        db.session.rollback()
        print(f"删除附件失败: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash(f'删除失败：{str(e)}', 'error')
            return redirect(url_for('tour_projects.edit_tour_project', project_id=project_id))
