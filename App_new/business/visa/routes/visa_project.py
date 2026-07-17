import shutil
from flask import current_app
import os
from datetime import datetime
import platform
import subprocess
from flask_login import login_required, current_user
from App_new.exts import db, csrf
from App_new.business.visa.models.Visamodels import VisaTypes, VisaDocuments, VisaLinks, VisaProject, VisaCountries, VisaSingaporeIdentity, VisaProjectFile, VisaFormCoordinate, VisaProjectFormData, VisaFormTemplate
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
    # 韩国(图片叠字) / 日本(可填 PDF)
    visa_type = visa_type or ''
    return '韩国' in visa_type or '日本' in visa_type

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
        search_contact = request.args.get('search_contact', '')
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

        # 应用国家筛选（按 country_name_EN，兼容旧 URL 里的中文值）
        if filter_country != 'all':
            from sqlalchemy import or_
            query = query.join(VisaTypes, VisaProject.visa_type == VisaTypes.visa_type)\
                .join(VisaCountries, VisaTypes.country_id == VisaCountries.id)\
                .filter(or_(
                    VisaCountries.country_name_EN == filter_country,
                    VisaCountries.country_name_CN == filter_country
                ))
            
        # 应用申请人姓名搜索
        if search_name:
            query = query.filter(VisaProject.applicant_name.like(f'%{search_name}%'))

        # 应用联系人搜索
        if search_contact:
            query = query.filter(VisaProject.contact_name.like(f'%{search_contact}%'))

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
        
        # 获取所有国家（按英文名排序，便于在下拉里键入字母快速定位）
        countries = VisaCountries.query.order_by(VisaCountries.country_name_EN).all()
        
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
                             search_contact=search_contact,
                             visa_types=visa_types,
                             countries=countries,
                             visa_categories=visa_categories,
                             project_links=project_links)

    except Exception as e:
        flash(f'获取项目列表时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))


@visa_project.route('/visa_processing', methods=['GET', 'POST'])
@login_required
@staff_only
def visa_processing():
    """签证处理页面路由（签证类型通过查询参数 visa_type 传入）"""
    try:
        # 签证类型改为查询参数传入：/visa_processing?visa_type=xxx
        visa_type = request.args.get('visa_type', '').strip()
        if not visa_type:
            flash('缺少签证类型参数', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))

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


# ============ 韩国签证「填写表格」：字段模板 + 项目填表值 ============
# 字段结构(标签/类型/选项)来自母版 FormSample.xls；填的值存 visa_project_form_data。

# 韩国签证填表分段：按坐标序列整数前缀(组号)归类，给每段一个可读标题
_KOREA_FORM_SECTIONS = {
    '1': '个人信息',
    '2': '停留信息',
    '3': '护照信息',
    '4': '联系方式 / 紧急联络人',
    '5': '婚姻 / 配偶 / 子女',
    '6': '学历',
    '7': '雇佣 / 公司',
    '8': '访问信息',
    '9': '邀请机构',
    '10': '费用 / 赞助人',
    '11': '其它',
    '12': '签名',
}

# 部分组内容太杂，只按组号归类会把不相干的字段堆在一张卡片里。
# 这里按坐标序列前缀再拆一层，命中则用细分标题，否则回落到组标题。
_KOREA_SUB_SECTIONS = (
    # 第 8 组「访问信息」：本次行程 / 韩国历史访问 / 其它国家历史访问
    ('8.1-', '申请访问目的'),
    ('8.2-', '申请访问目的'),
    ('8.3-', '申请访问目的'),
    ('8.4-', '申请访问目的'),
    ('8.5-', '申请访问目的'),
    ('8.6-', '历史访问信息'),        # 是否去过韩国 + 次数 / 目的 / 出入境日期
    ('8.7-', '历史访问其它国家'),    # 近 5 年访问其它国家(最多 4 条)
)


def _korea_section_title(seq, group):
    """字段所属分段标题：先看细分前缀，再回落到组标题。"""
    for prefix, title in _KOREA_SUB_SECTIONS:
        if seq.startswith(prefix):
            return title
    return _KOREA_FORM_SECTIONS.get(group, f'组{group}')


# 这些前缀下「一条记录一行」：同一条记录的几个字段排在同一行，方便按条录入
_KOREA_ROW_GROUPED_PREFIXES = ('8.6-', '8.7-')

# 行分组推不出来的字段，按 seq 显式指定行 id
_KOREA_ROW_OVERRIDES = {
    # 历史访问信息：是否去过+去过几次 挤一行；其余 8.6-N-* 按前缀各自成行
    '8.6-0-': '8.6-r1',
    '8.6-1-': '8.6-r1',
}


def _korea_row_key(seq):
    """行分组 id：同 id 的字段在前端排一行；None 表示不参与行分组。

    8.7-1-1/8.7-1-2/8.7-1-3(国家1 的 名字/目的/时间) → '8.7-1'
    8.7-0-(是否访问过其它国家) → '8.7-0'，自己独占一行
    """
    if seq in _KOREA_ROW_OVERRIDES:
        return _KOREA_ROW_OVERRIDES[seq]
    for prefix in _KOREA_ROW_GROUPED_PREFIXES:
        if seq.startswith(prefix):
            parts = seq.split('-')
            return f'{parts[0]}-{parts[1]}' if len(parts) >= 2 else seq
    return None


# 母版 FormSample.xls 里缺、但表格上确实存在的字段，在读母版后补进来。
# 韩国表格「8.6 历史访问韩国」那张表有 5 行，母版只给了第 1 行(8.6-2-*)，
# 这里补第 2~5 行。母版是共用资料且不入 Git(资源/ 已忽略)，改母版线上还得重传，
# 放代码里可随 git 部署；母版将来真加了同 seq 的行，下面的补充会自动跳过。
# 坐标另存 visa_form_coordinates，见 scripts/20260717_add_korea_visit_history_rows.py。
_KOREA_EXTRA_FIELDS = [
    # (seq, 标签)；第 N 次访问记录 → 8.6-(N+1)-1 目的 / 8.6-(N+1)-2 出入境日期
    (f'8.6-{n + 1}-{col}', label)
    for n in range(2, 6)
    for col, label in ((1, f'入境韩国目的{n}'), (2, f'入境和出境韩国日期{n}'))
]


def _korea_extra_field(seq, label, page='PAGE03'):
    """把 _KOREA_EXTRA_FIELDS 的 (seq, 标签) 补成与母版字段同构的结构。"""
    group = seq.split('.')[0].split('-')[0]
    return {
        'page': page,
        'seq': seq,
        'type': '填写',
        'section': _korea_section_title(seq, group),
        'form': label,
        'label': label,
        'ctype': 'text',
        'options': [],
        'remark': '',
        'editable': True,
        'applicant': True,   # 与第 1 行(母版 8.6-2-* 标 Y)保持一致
        'default': '',
        'row': _korea_row_key(seq),
    }


# 母版里标了「是否修改=N」但实际应由填表人自行填写/留空的字段。
# 母版的 DETAIL 只是样例数据(如某个新加坡地址)，不能当固定默认值用。
_KOREA_FORCE_EDITABLE_SEQS = {
    '4.2-',  # 其它地址：申请人可填可不填
}


def _korea_master_template_path():
    """韩国签证母版 FormSample.xls 路径(共用资料)"""
    from App_new.config import Config
    return os.path.join(Config.PROJECT_ROOT, '资源', '签证', '韩国签证', '共用资料', 'FormSample.xls')


def _cell_str(v):
    """Excel 单元格 → 干净字符串(NaN/None → '')"""
    import pandas as pd
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    return str(v).strip()


def _parse_choice_options(remark):
    """从 Remark 解析选项，如 "男：1)/女：2" → [{value,label}]"""
    import re
    opts = []
    if not remark:
        return opts
    for part in str(remark).split('/'):
        m = re.search(r'(.+?)[：:]\s*([0-9]+)', part)
        if m:
            opts.append({'value': m.group(2).strip(), 'label': m.group(1).strip()})
    return opts


def _korea_template_fields():
    """读母版 FormSample.xls，返回填表字段结构列表。

    每项: {page, seq, type(填写/选择), form(标签), remark(提示/选项), editable, applicant, default}
    - type '选择' 用 remark 里的 "男：1)/女：2" 生成下拉；'填写' 用文本框
    - editable=False(是否修改=N，且不在 _KOREA_FORCE_EDITABLE_SEQS 里) 的是固定默认值，前端只读
    - default 仅对固定字段有意义(母版里 Y 字段是样例数据，不作默认)
    - 母版缺的字段由 _KOREA_EXTRA_FIELDS 补齐(如历史访问韩国的第 2~5 行)
    """
    import pandas as pd
    path = _korea_master_template_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f'母版模板不存在: {path}')
    df = pd.read_excel(path, sheet_name='Sheet1')
    fields = []
    for _, row in df.iterrows():
        page = _cell_str(row.get('PAGE'))
        seq = _cell_str(row.get('坐标序列'))
        if not page or not seq:
            continue  # 跳过分隔/空行
        ftype = _cell_str(row.get('类型')) or '填写'
        editable = (_cell_str(row.get('是否修改')).upper() == 'Y'
                    or seq in _KOREA_FORCE_EDITABLE_SEQS)
        group = seq.split('.')[0].split('-')[0]  # 取整数前缀作组号
        remark = _cell_str(row.get('Remark'))
        form = _cell_str(row.get('FORM'))
        is_choice = (ftype == '选择')
        fields.append({
            'page': page,
            'seq': seq,
            'type': ftype,
            'section': _korea_section_title(seq, group),
            'row': _korea_row_key(seq),
            'form': form,
            # 统一字段结构（前端通用）
            'label': form or seq,
            'ctype': 'select' if is_choice else 'text',
            'options': _parse_choice_options(remark) if is_choice else [],
            'remark': remark,
            'editable': editable,
            'applicant': _cell_str(row.get('是否申请人提供信息')).upper() == 'Y',
            'default': _cell_str(row.get('DETAIL')) if not editable else '',
        })

    # 补齐母版缺的字段(见 _KOREA_EXTRA_FIELDS)；母版已有同 seq 则以母版为准
    have = {f['seq'] for f in fields}
    fields.extend(_korea_extra_field(seq, label)
                  for seq, label in _KOREA_EXTRA_FIELDS if seq not in have)
    return fields


# ============ 日本签证「填写表格」：字段来自可填 PDF（AcroForm/XFA）============
# PDF 自带字段名(seq)、/TU 标签、下拉选项；单选框 /TU 是代号，需手工给标签。
# 单选框：按 PDF 内文字 + 控件位置确定含义与「开关值→标签」。
# key 用完整短名（RB5 六题各不相同）；options 的 value 必须是控件真实开关值。
_JP_YESNO = [{'value': '0', 'label': 'Yes 是'}, {'value': '1', 'label': 'No 否'}]
_JAPAN_RADIO_LABELS = {
    # 注意：RB1 真实开关值是 0(Male)/1(Female)，非 M/F（M/F 只是 /Opt 显示串）
    'RB1[0]': {'label': 'Sex 性别',
               'options': [{'value': '0', 'label': 'Male 男'}, {'value': '1', 'label': 'Female 女'}]},
    'RB1[1]': {'label': 'Sex 性别',
               'options': [{'value': '0', 'label': 'Male 男'}, {'value': '1', 'label': 'Female 女'}]},
    'RB3[0]': {'label': 'Passport type 护照类型', 'options': [
        {'value': '0', 'label': 'Diplomatic 外交'}, {'value': '1', 'label': 'Official 公务'},
        {'value': '2', 'label': 'Ordinary 普通'}, {'value': '3', 'label': 'Other 其它'}]},
    'RB2[0]': {'label': 'Marital status 婚姻状况', 'options': [
        {'value': '0', 'label': 'Single 未婚'}, {'value': '1', 'label': 'Married 已婚'},
        {'value': '3', 'label': 'Divorced 离异'}, {'value': '2', 'label': 'Widowed 丧偶'}]},
    # RB5 六个「Have you ever…」是否题（按控件 y 位置从上到下对应）
    'RB5[3]': {'label': '曾在任何国家被判罪/违法? (crime or offence)', 'options': _JP_YESNO},
    'RB5[0]': {'label': '曾被判 1 年以上监禁? (imprisonment 1yr+)', 'options': _JP_YESNO},
    'RB5[1]': {'label': '曾因毒品犯罪被判刑? (drug offence)', 'options': _JP_YESNO},
    'RB5[5]': {'label': '曾从事卖淫相关活动? (prostitution)', 'options': _JP_YESNO},
    'RB5[4]': {'label': '曾贩卖人口或教唆协助? (trafficking)', 'options': _JP_YESNO},
    'RB5[2]': {'label': '曾被遣返/因逾期滞留被驱逐? (deported/overstay)', 'options': _JP_YESNO},
}

# 部分字段 /TU 只是 Name/Address/Tel（多个区块重名），给清晰标签避免混淆
_JAPAN_FIELD_LABELS = {
    'emp_name[0]': 'Employer name 雇主名称',
    'emp_adr[0]': 'Employer address 雇主地址',
    'emp_tel[0]': 'Employer tel 雇主电话',
    'emp_name[1]': '在日住宿/联系人 名称',
    'emp_adr[1]': '在日住宿/联系人 地址',
    'emp_tel[1]': '在日住宿/联系人 电话',
    'T0[1]': 'Current residential address 现住址',
    'T97[0]': 'Tel 电话',
    'T3[0]': 'Mobile 手机',
    'T3[1]': 'E-Mail 邮箱',
    'guarantor_name[0]': 'Guarantor name 担保人姓名',
    'guarantor_adr[0]': 'Guarantor address 担保人地址',
    'guarantor_tel[0]': 'Guarantor tel 担保人电话',
    'T25[0]': 'Relationship 关系(担保人)',
    'T5[1]': 'Nationality & status 国籍/身份(担保人)',
    'T19[0]': 'Inviter name 邀请人姓名',
    'T23[0]': 'Inviter address 邀请人地址',
    'T10[0]': 'Inviter tel 邀请人电话',
    'T25[1]': 'Relationship 关系(邀请人)',
    'T14[1]': 'Inviter DOB 邀请人生日',
    'T5[2]': 'Nationality & status 国籍/身份(邀请人)',
    'T5[3]': 'Inviter profession 邀请人职业',
}

# 日本填表分段：字段短名 → 段落标题（按内容归类，顺序即展示顺序）
_JAPAN_SECTIONS = [
    ('护照信息', ['T49[0]', 'T50[0]', 'T53[0]', 'T57[0]', 'T57[1]', 'T59[0]', 'T34[0]']),
    ('个人信息', ['T2[0]', 'T7[0]', 'T14[0]', 'T16[0]', 'RB1[0]', 'T16[1]', 'T37[0]', 'RB2[0]', 'RB3[0]']),
    ('联系方式', ['T0[1]', 'T97[0]', 'T3[0]', 'T3[1]']),
    ('工作 / 雇主', ['emp_name[0]', 'emp_adr[0]', 'emp_tel[0]', 'T5[0]']),
    ('访日信息', ['T68[2]', 'T68[3]', 'T66[0]', 'T68[0]', 'T68[1]', 'T62[0]', 'T64[0]',
                  'emp_name[1]', 'emp_adr[1]', 'emp_tel[1]']),
    ('在日担保人', ['guarantor_name[0]', 'guarantor_adr[0]', 'guarantor_tel[0]', 'T25[0]']),
    ('在日邀请人', ['T19[0]', 'T23[0]', 'T10[0]', 'T25[1]', 'T14[1]', 'T5[1]', 'T5[2]', 'T5[3]', 'RB1[1]']),
    ('配偶 / 家属', ['T16[2]']),
    ('声明事项', ['RB5[0]', 'RB5[1]', 'RB5[2]', 'RB5[3]', 'RB5[4]', 'RB5[5]']),
    ('备注 / 申请', ['T28[0]', 'T28[1]', 'T150[0]']),
]
# 短名 → (段落标题, 段落序, 段内序)
_JAPAN_SECTION_MAP = {}
for _si, (_title, _names) in enumerate(_JAPAN_SECTIONS):
    for _fi, _n in enumerate(_names):
        _JAPAN_SECTION_MAP[_n] = (_title, _si, _fi)

# 第2页字段的 标签+段落+段内序（短名在第2页内唯一，按 PDF 位置核对：
# 上半块=担保人，下半块=邀请人）。覆盖第1页同短名映射，修正 T5[0]/T14[0] 跨页冲突。
_JAPAN_PAGE2 = {
    # 在日担保人（页面上半块）
    'guarantor_name[0]': ('Guarantor name 担保人姓名', '在日担保人', 0),
    'guarantor_adr[0]': ('Guarantor address 担保人地址', '在日担保人', 1),
    'guarantor_tel[0]': ('Guarantor tel 担保人电话', '在日担保人', 2),
    'T14[1]': ('Guarantor DOB 担保人生日', '在日担保人', 3),
    'T25[1]': ('Relationship 关系(担保人)', '在日担保人', 4),
    'T5[0]': ('Guarantor profession 担保人职业', '在日担保人', 5),
    'T5[1]': ('Nationality & status 国籍/身份(担保人)', '在日担保人', 6),
    # 在日邀请人（页面下半块）
    'T19[0]': ('Inviter name 邀请人姓名', '在日邀请人', 0),
    'T23[0]': ('Inviter address 邀请人地址', '在日邀请人', 1),
    'T10[0]': ('Inviter tel 邀请人电话', '在日邀请人', 2),
    'T14[0]': ('Inviter DOB 邀请人生日', '在日邀请人', 3),
    'T25[0]': ('Relationship 关系(邀请人)', '在日邀请人', 4),
    'T5[3]': ('Inviter profession 邀请人职业', '在日邀请人', 5),
    'T5[2]': ('Nationality & status 国籍/身份(邀请人)', '在日邀请人', 6),
    'RB1[1]': (None, '在日邀请人', 7),  # 单选，标签用 radio 表
    # 配偶 / 家属
    'T16[2]': ("Partner's profession 配偶/家属职业", '配偶 / 家属', 0),
    # 声明事项（RB5 标签用 radio 表）
    'RB5[0]': (None, '声明事项', 0), 'RB5[1]': (None, '声明事项', 1),
    'RB5[2]': (None, '声明事项', 2), 'RB5[3]': (None, '声明事项', 3),
    'RB5[4]': (None, '声明事项', 4), 'RB5[5]': (None, '声明事项', 5),
    # 备注 / 申请
    'T28[0]': ('Remarks 备注', '备注 / 申请', 0),
    'T28[1]': ('Yes 的详情说明 (details)', '备注 / 申请', 1),
    'T150[0]': ('Date of application 申请日期', '备注 / 申请', 2),
}
# 段落全局顺序
_JAPAN_SECTION_ORDER = {t: i for i, t in enumerate(
    ['护照信息', '个人信息', '联系方式', '工作 / 雇主', '访日信息',
     '在日担保人', '在日邀请人', '配偶 / 家属', '声明事项', '备注 / 申请', '其它'])}


def _japan_master_pdf_path():
    """日本签证母版可填 PDF 路径(共用资料)"""
    from App_new.config import Config
    return os.path.join(Config.PROJECT_ROOT, '资源', '签证', '日本签证', '共用资料', 'visa application form.pdf')


def _japan_template_fields():
    """读母版 PDF 的 AcroForm，返回统一字段结构列表。

    seq=PDF字段名；label=/TU；ctype=text/select/radio；options 来自 /Opt。
    同名字段跨页重复的只取一次（填充时按名字会一并填）。
    """
    from pypdf import PdfReader
    path = _japan_master_pdf_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f'日本母版 PDF 不存在: {path}')
    reader = PdfReader(path)
    all_fields = reader.get_fields() or {}

    type_map = {'/Tx': 'text', '/Ch': 'select', '/Btn': 'radio'}
    fields = []
    for name, f in all_fields.items():
        ft = f.get('/FT')
        if ft not in type_map:
            continue  # 跳过 #area 容器等非输入字段
        # 用全限定名作 seq：页1、页2 的同名字段(如 T5[0]/T14[0])是不同键，各填各的，
        # 避免跨页短名冲突导致申请人的值漏进第2页担保人/邀请人栏。
        seq = str(name)
        short = seq.split('.')[-1]
        page_idx = 2 if 'Page2[0]' in seq else 1

        tu = _cell_str(f.get('/TU'))
        ctype = type_map[ft]

        # 解析选项
        options = []
        opt = f.get('/Opt')
        if opt:
            for it in opt:
                if hasattr(it, '__len__') and not isinstance(it, str) and len(it) >= 2:
                    options.append({'value': str(it[0]), 'label': str(it[1])})
                else:
                    options.append({'value': str(it), 'label': str(it)})

        # 标签 + 段落：第2页用专属映射(短名在页内唯一)，第1页用通用映射
        if page_idx == 2 and short in _JAPAN_PAGE2:
            lbl, section, in_order = _JAPAN_PAGE2[short]
            label = lbl
        else:
            label = _JAPAN_FIELD_LABELS.get(short, tu or short)
            sec_info = _JAPAN_SECTION_MAP.get(short)
            section = sec_info[0] if sec_info else '其它'
            in_order = sec_info[2] if sec_info else 0

        # 单选框：正确选项 + 手工标签
        if ft == '/Btn':
            rb = _JAPAN_RADIO_LABELS.get(short)
            if rb:
                options = [dict(o) for o in rb['options']]
                if not label:
                    label = rb['label']
        if not label:
            label = tu or short

        sec_order = _JAPAN_SECTION_ORDER.get(section, 99)
        fields.append({
            'page': f'PAGE0{page_idx}',
            'seq': seq,
            'section': section,
            '_sort': (page_idx, sec_order, in_order),
            'label': label,
            'ctype': ctype,
            'options': options,
            'remark': '',
            'editable': True,
            'applicant': False,
            'default': '',
        })
    # 按 页 → 段落序 → 段内序 排列
    fields.sort(key=lambda f: f['_sort'])
    for f in fields:
        f.pop('_sort', None)
    return fields


def _project_template_fields(project):
    """按签证类型选择字段来源：日本→PDF，其余(韩国)→Excel 母版。"""
    if '日本' in (project.visa_type or ''):
        return _japan_template_fields()
    return _korea_template_fields()


def _project_form_values(project):
    """项目已填的值 {seq: detail}。优先数据库，其次旧的 FormSample.xls，最后空。"""
    rows = VisaProjectFormData.query.filter_by(project_id=project.id).all()
    if rows:
        return {r.seq: (r.detail or '') for r in rows}

    # 日本用 PDF 字段名作 key，与韩国 Excel 的坐标序列不通用，不做 Excel 回退
    if '日本' in (project.visa_type or ''):
        return {}

    # 兼容老韩国项目：库里没有则尝试读项目文件夹里已填好的 FormSample.xls。
    # 历史项目该文件可能在根目录，也可能在 temp/ 或 visa_form/ 子目录，依次查找。
    from App_new.config import Config
    base = os.path.join(str(Config.VISA_PROJECTS_PATH), project.project_folder_name or '')
    for sub in ('', 'temp', 'visa_form', 'vsia_form'):
        xls = os.path.join(base, sub, 'FormSample.xls')
        if not os.path.exists(xls):
            continue
        try:
            import pandas as pd
            df = pd.read_excel(xls, sheet_name='Sheet1')
            values = {}
            for _, row in df.iterrows():
                seq = _cell_str(row.get('坐标序列'))
                detail = _cell_str(row.get('DETAIL'))
                if seq and detail:
                    values[seq] = detail
            if values:  # 找到有内容的就用它
                current_app.logger.info(f'项目{project.id} 从 {xls} 读到 {len(values)} 条填表值')
                return values
        except Exception as e:
            current_app.logger.warning(f'读取项目 FormSample.xls 失败({project.id}, {xls}): {e}')
    return {}


def _resolve_form_values(project):
    """{seq: 值}，值 = 库值→(韩国)固定默认。用于日本 PDF 填充与通用判断。"""
    fields = _project_template_fields(project)
    values = _project_form_values(project)
    out = {}
    for f in fields:
        v = values.get(f['seq'])
        if v is None or v == '':
            v = f.get('default') or ''
        out[f['seq']] = v
    return out


def _resolve_form_rows(project):
    """构建生成表格所需的行: [{PAGE, 坐标序列, 类型, DETAIL}]，值 = 库值→旧Excel→固定默认。"""
    fields = _korea_template_fields()
    values = _project_form_values(project)
    rows = []
    for f in fields:
        detail = values.get(f['seq'])
        if detail is None or detail == '':
            detail = f['default']  # 固定字段回退默认；可填字段为空则空(生成时会跳过)
        rows.append({
            'PAGE': f['page'],
            '坐标序列': f['seq'],
            '类型': f['type'],
            'DETAIL': detail,
        })
    return rows


@visa_project.route('/<int:project_id>/form-data', methods=['GET'])
@login_required
@staff_only
def get_project_form_data(project_id):
    """读取项目填表表单(字段结构 + 已填值)，供详情页「填写表格」渲染。"""
    project = VisaProject.query.get_or_404(project_id)
    if not is_visa_type_supported_for_form_generation(project.visa_type or ''):
        return jsonify({'success': False, 'message': f'签证类型 "{project.visa_type}" 暂不支持填表'}), 400
    try:
        fields = _project_template_fields(project)
    except FileNotFoundError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except ImportError as e:
        return jsonify({'success': False, 'message': f'缺少依赖: {e}（日本签证需 pypdf）'}), 500
    values = _project_form_values(project)
    out = []
    for f in fields:
        v = values.get(f['seq'])
        if v is None or v == '':
            v = f['default']
        out.append({**f, 'value': v})
    return jsonify({'success': True, 'fields': out})


@visa_project.route('/<int:project_id>/form-data', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def save_project_form_data(project_id):
    """保存项目填表值到 visa_project_form_data（整体替换该项目的记录）。

    请求体: {"values": {"1.1-1": "LYU", "1.4-": "23 MAR 1989", ...}}
    只存非空值；页码从母版模板匹配。
    """
    project = VisaProject.query.get_or_404(project_id)
    if not is_visa_type_supported_for_form_generation(project.visa_type or ''):
        return jsonify({'success': False, 'message': f'签证类型 "{project.visa_type}" 暂不支持填表'}), 400

    data = request.get_json(silent=True) or {}
    values = data.get('values') or {}
    if not isinstance(values, dict):
        return jsonify({'success': False, 'message': 'values 必须是 {seq: detail} 对象'}), 400

    # seq → page 映射(用于给记录补页码)
    try:
        seq_page = {f['seq']: f['page'] for f in _project_template_fields(project)}
    except Exception:
        seq_page = {}

    try:
        # 整体替换：先删该项目旧记录，再插入非空值
        VisaProjectFormData.query.filter_by(project_id=project.id).delete()
        saved = 0
        for seq, detail in values.items():
            detail = (str(detail) if detail is not None else '').strip()
            if not detail:
                continue
            db.session.add(VisaProjectFormData(
                project_id=project.id,
                page=seq_page.get(seq),
                seq=seq,
                detail=detail,
            ))
            saved += 1
        db.session.commit()
        return jsonify({'success': True, 'saved': saved})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'保存填表数据失败({project_id}): {e}')
        return jsonify({'success': False, 'message': f'保存失败: {e}'}), 500


def _project_master_template_target(project):
    """返回项目填表母版的 (目标路径, 允许扩展名集合, 类型说明)。不支持则 (None, None, None)。

    母版为「共用资料」，按签证类型固定命名，上传即覆盖该类型所有项目共用的母版。
    """
    vt = project.visa_type or ''
    if '日本' in vt:
        return _japan_master_pdf_path(), {'pdf'}, '日本可填 PDF 母版'
    if '韩国' in vt:
        return _korea_master_template_path(), {'xls', 'xlsx'}, '韩国 Excel 母版'
    return None, None, None


@visa_project.route('/<int:project_id>/upload-master-template', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def upload_master_template(project_id):
    """上传当前签证类型的填表母版文件（共用资料），供填表页读取字段结构。

    注意：母版按签证类型共用，上传会覆盖该类型所有项目使用的母版（旧文件自动备份）。
    """
    project = VisaProject.query.get_or_404(project_id)
    target_path, allowed_exts, kind = _project_master_template_target(project)
    if not target_path:
        return jsonify({'success': False, 'message': f'签证类型 "{project.visa_type}" 暂不支持上传母版'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_exts:
        return jsonify({'success': False,
                        'message': f'{kind}需 {"/".join(sorted(allowed_exts))} 格式，当前为 .{ext}'}), 400

    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        # 已存在则先备份旧母版，避免误覆盖不可恢复
        if os.path.exists(target_path):
            import shutil
            from datetime import datetime
            bak = f"{target_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(target_path, bak)
        file.save(target_path)
        current_app.logger.info(f'项目{project_id} 上传{kind}: {target_path}')
        return jsonify({'success': True, 'message': f'{kind}上传成功，可继续填表'})
    except Exception as e:
        current_app.logger.error(f'上传母版失败({project_id}): {e}')
        return jsonify({'success': False, 'message': f'上传失败: {e}'}), 500


@visa_project.route('/<int:project_id>/fill-form', methods=['GET'])
@login_required
@staff_only
def fill_form_page(project_id):
    """填写签证表格的独立页面（数据仍走 /form-data 接口）。

    ?page= 指定默认打开的分页，支持 "1" / "PAGE01" 两种写法；
    页码集合由母版决定，故只做格式清洗，真正的匹配在前端渲染时做。
    """
    project = VisaProject.query.get_or_404(project_id)
    if not is_visa_type_supported_for_form_generation(project.visa_type or ''):
        flash(f'签证类型 "{project.visa_type}" 暂不支持填表', 'warning')
        return redirect(url_for('visa_project.visa_detail', project_id=project.id))
    page = (request.args.get('page') or '').strip()[:10]
    return render_template('business/visa/签证项目管理/visa_form_fill.html',
                           project=project, active_page=page)


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
        if not project.applicant_name:
            missing_fields.append('申请人姓名')
        if '韩国' in (project.visa_type or '') and not project.singapore_status:
            missing_fields.append('新加坡身份')

        if missing_fields:
            current_app.logger.warning(f"项目信息不完整，缺少字段: {', '.join(missing_fields)}")
            return jsonify({
                'success': False,
                'message': f'项目信息不完整，请确保以下字段已填写: {", ".join(missing_fields)}'
            }), 400

        # 如果没有HID，给出警告但不阻止（表格中HID字段会为空）
        if not project.hid_or_serial:
            current_app.logger.warning(f"项目没有HID/序列号，表格中该字段将为空")

        # 生成表格的逻辑 - 优先使用数据库中保存的项目文件夹名称
        visa_folder = project.project_folder_name
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

        # 日本签证：填充可填 PDF（AcroForm），输出 Application Form.pdf 到项目文件夹
        if '日本' in project.visa_type:
            values = _resolve_form_values(project)
            if not any((v or '').strip() for v in values.values()):
                return jsonify({
                    'success': False,
                    'message': '尚未填写表格数据，请先点击「填写表格」录入后再生成'
                }), 400
            radio_fields = {f['seq'] for f in _project_template_fields(project)
                            if f.get('ctype') == 'radio'}
            from App_new.utils.VisaForm import VisasUtils
            out_path = VisasUtils.japan_visa_fill_form(visa_folder, values, radio_fields=radio_fields)
            current_app.logger.info(f'日本签证 PDF 生成: {out_path}')
            return jsonify({'success': True, 'message': '表格生成成功',
                            'file': os.path.basename(out_path)})

        # 韩国签证资源(页面底图 Form-page-N.jpg)必须存在
        from App_new.config import Config
        source_path = Config.PROJECT_ROOT / "资源" / "签证" / "韩国签证" / "source"
        current_app.logger.info(f"检查韩国签证资源路径: {source_path}")
        if not source_path.exists():
            current_app.logger.warning(f"韩国签证资源文件不存在: {source_path}")
            return jsonify({
                'success': False,
                'message': f'韩国签证资源文件不存在: {source_path}'
            }), 400

        # 填表值改从数据库读取(坐标也已入库)，不再依赖项目文件夹里的 FormSample.xls；
        # 老项目库里没有时，_resolve_form_rows 会自动回退读旧的 FormSample.xls。
        form_rows = _resolve_form_rows(project)
        if not any((r.get('DETAIL') or '').strip() for r in form_rows):
            return jsonify({
                'success': False,
                'message': '尚未填写表格数据，请先点击「填写表格」录入后再生成'
            }), 400

        # 根据签证类型调用相应的表格生成函数
        if '韩国' in project.visa_type:
            # 调用韩国签证表格生成函数
            from App_new.utils.VisaForm import VisasUtils
            VisasUtils.korea_visa_fill_form(
                visa_folder=visa_folder, static_path=str(static_path), form_rows=form_rows)
        else:
            return jsonify({
                'success': False,
                'message': f'签证类型 "{project.visa_type}" 的表格生成功能尚未实现'
            }), 400
        
        return jsonify({'success': True, 'message': '表格生成成功', 'file': 'visa_form.pdf'})
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


def _visa_category(visa_type):
    """签证类别：japan / korea / ''（模板按此隔离，字段体系不同）"""
    visa_type = visa_type or ''
    if '日本' in visa_type:
        return 'japan'
    if '韩国' in visa_type:
        return 'korea'
    return ''


@visa_project.route('/form-templates', methods=['GET'])
@login_required
@staff_only
def list_form_templates():
    """列出填表模板（可按 category 过滤）。"""
    category = (request.args.get('category') or '').strip()
    q = VisaFormTemplate.query
    if category:
        q = q.filter_by(visa_category=category)
    items = q.order_by(VisaFormTemplate.updated_at.desc()).all()
    return jsonify({'success': True, 'templates': [
        {'id': t.id, 'name': t.name, 'category': t.visa_category} for t in items]})


@visa_project.route('/form-templates', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def create_form_template():
    """保存填表模板：{name, category, values:{seq:value}}。同名+同类别则覆盖。"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    values = data.get('values') or {}
    if not name:
        return jsonify({'success': False, 'message': '请填写模板名称'}), 400
    if not isinstance(values, dict):
        return jsonify({'success': False, 'message': 'values 必须是对象'}), 400
    payload = json.dumps({k: v for k, v in values.items() if str(v).strip()}, ensure_ascii=False)
    tpl = VisaFormTemplate.query.filter_by(name=name, visa_category=category).first()
    try:
        if tpl:
            tpl.data = payload  # 覆盖同名模板
        else:
            tpl = VisaFormTemplate(name=name, visa_category=category, data=payload)
            db.session.add(tpl)
        db.session.commit()
        return jsonify({'success': True, 'id': tpl.id, 'name': tpl.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'保存失败: {e}'}), 500


@visa_project.route('/form-templates/<int:tid>', methods=['GET'])
@login_required
@staff_only
def get_form_template(tid):
    """取模板的字段值。"""
    tpl = VisaFormTemplate.query.get_or_404(tid)
    try:
        values = json.loads(tpl.data or '{}')
    except Exception:
        values = {}
    return jsonify({'success': True, 'name': tpl.name, 'values': values})


@visa_project.route('/form-templates/<int:tid>', methods=['DELETE'])
@csrf.exempt
@login_required
@staff_only
def delete_form_template(tid):
    """删除模板。"""
    tpl = VisaFormTemplate.query.get_or_404(tid)
    try:
        db.session.delete(tpl)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {e}'}), 500


@visa_project.route('/<int:project_id>/download-form', methods=['GET'])
@login_required
@staff_only
def download_form(project_id):
    """下载已生成的签证表格 PDF（韩国 visa_form.pdf / 日本 Application Form.pdf）。"""
    project = VisaProject.query.get_or_404(project_id)
    from App_new.config import Config
    folder = os.path.join(str(Config.VISA_PROJECTS_PATH), project.project_folder_name or '')
    fname = 'Application Form.pdf' if '日本' in (project.visa_type or '') else 'visa_form.pdf'
    path = os.path.join(folder, fname)
    if not os.path.exists(path):
        return jsonify({'success': False, 'message': '未找到已生成的表格，请先点击「生成表格」'}), 404
    dl_name = f"{(project.applicant_name or 'visa').strip()}_{(project.visa_type or 'form').strip()}.pdf"
    from flask import send_file
    try:
        return send_file(path, as_attachment=True, download_name=dl_name)
    except TypeError:
        # 兼容旧版 Flask
        return send_file(path, as_attachment=True, attachment_filename=dl_name)


""" 签证详细 开始 """
@visa_project.route('/visa_detail/<project_name>')
@visa_project.route('/visa_detail/id/<int:project_id>')
@login_required
@staff_only
def visa_detail(project_name=None, project_id=None):
    """签证详情页面路由"""
    try:
        # 获取项目信息
        project = None
        if project_id:
            try:
                project = VisaProject.query.get_or_404(project_id)
            except Exception as e:
                flash(f'项目不存在或已被删除', 'error')
                return redirect(url_for('visa_project.show_current_all_projects'))
        else:
            project = VisaProject.query.filter_by(project_folder_name=project_name).first()
            if not project:
                flash(f'项目不存在或已被删除', 'error')
                return redirect(url_for('visa_project.show_current_all_projects'))

        # 检查项目是否有签证类型
        if not project.visa_type:
            flash(f'项目缺少签证类型信息', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))

        # 获取签证类型信息
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        if not types_info:
            flash(f'签证类型 "{project.visa_type}" 不存在', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))

        # 获取相关链接 - 优先通过visa_type_id查找，没有数据时再通过visa_countries_id查找
        links = VisaLinks.query.filter_by(visa_type_id=types_info.id).order_by(VisaLinks.name.asc()).all()

        # 如果通过visa_type_id没有找到链接，则通过visa_countries_id查找
        if not links and types_info.country_id:
            links = VisaLinks.query.filter_by(visa_countries_id=types_info.country_id).order_by(VisaLinks.name.asc()).all()

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
                'additional_info': doc_info['additional_info'],
                'applicant_additional_info': doc_info['applicant_additional_info']
            }

        # 单独处理SHARE共用资料显示
        if share_identity_id:
            share_doc_info = VisaDocuments.get_document_info(types_info.id, share_identity_id)
            document_data['SHARE'] = {
                'document_info': share_doc_info['document_info'],
                'additional_info': share_doc_info['additional_info'],
                'applicant_additional_info': share_doc_info['applicant_additional_info']
            }
        
        # 获取项目的资料准备状态
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus, VisaDocumentsList
        project_document_statuses = VisaProjectDocumentStatus.query.filter_by(
            project_id=project.id
        ).all()

        # 构建 中文名->英文名 对照表（用于资料卡片显示英文名称）
        name_en_map = {
            d.name: d.name_en
            for d in VisaDocumentsList.query.filter(VisaDocumentsList.name_en.isnot(None)).all()
            if d.name_en
        }

        # 将资料状态转换为字典格式，方便模板使用
        document_statuses = {}
        for status in project_document_statuses:
            document_statuses[status.document_name] = {
                'id': status.id,
                'is_ready': status.is_ready,
                'notes': status.notes,
                'document_type': status.document_type,
                'name_en': name_en_map.get(status.document_name, '')
            }
        
        # 检查项目是否已关联HID和REF
        has_header = project.header_id is not None
        has_ref = project.ref_id is not None

        # 模板文件：共用模板 + 项目身份对应的模板，方便下载
        from App_new.business.visa.models.Visamodels import VisaTemplateFiles
        specific_identity = None
        if project.singapore_status and project.singapore_status != 'SHARE':
            specific_identity = VisaSingaporeIdentity.query.filter_by(
                identity_zh=project.singapore_status
            ).first()
        identity_filter = [VisaTemplateFiles.singapore_identity_id.is_(None)]
        if specific_identity:
            identity_filter.append(VisaTemplateFiles.singapore_identity_id == specific_identity.id)
        template_files = VisaTemplateFiles.query.filter(
            VisaTemplateFiles.visa_type_id == types_info.id,
            VisaTemplateFiles.is_active == True,
            db.or_(*identity_filter)
        ).order_by(VisaTemplateFiles.template_type, VisaTemplateFiles.template_name).all()

        return render_template('business/visa/签证项目管理/visa_project_detail.html',
                             project=project,
                             types_info=types_info,
                             links=links,
                             document_data=document_data,
                             document_statuses=document_statuses,
                             template_files=template_files,
                             specific_identity=specific_identity,
                             has_header=has_header,
                             has_ref=has_ref)
                             
    except Exception as e:
        # 打印完整堆栈，方便定位真实错误
        import traceback
        current_app.logger.error(f"获取签证详情失败 (project_id={project_id}, project_name={project_name}): {str(e)}")
        current_app.logger.error(traceback.format_exc())
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
        
        # 获取经办人ID
        staff_id_value = current_user.id if current_user else None

        # 创建或获取项目主表（HID）
        header = None
        if not project.header_id:
            # 获取"个人"公司记录
            from App_new.business.projects.models.project import CustomerCompany
            personal_company = CustomerCompany.query.filter_by(company_code='PERSONAL').first()
            if not personal_company:
                personal_company = CustomerCompany.query.filter_by(company_name='个人').first()
            if not personal_company:
                return jsonify({
                    'success': False,
                    'message': '未找到"个人"客户公司记录，请先在系统中创建'
                }), 400

            # 生成HID
            hid = ProjectHeader.generate_hid()

            # 创建项目主表（staff_name 由事件自动同步）
            header = ProjectHeader(
                hid=hid,
                desc=f"{project.applicant_name} {project.visa_type}签证项目",
                company_id=personal_company.id,
                contact=project.contact_name or project.applicant_name,
                staff_id=staff_id_value,
                currency='SGD',
                type='visa',
                status='active'
            )
            header.leader_name = header.staff_name or project.applicant_name
            db.session.add(header)
            db.session.flush()  # 获取header.id
            
            # 更新签证项目的header_id和hid_or_serial
            project.header_id = header.id
            project.hid_or_serial = hid  # 自动填充HID到hid_or_serial字段

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

            # 生成签证名称（用真实国家英文名 + 签证类型，避免出现 "OTHER TOURIST VISA"）
            visa_name = f"{country_name} {project.visa_type}"  # 中文版保留兼容
            visa_type_en = (getattr(types_info, 'visa_type_en', None) or '') if types_info else ''
            visa_name_en = f"{(country_name_en or country_name or '').strip()} {(visa_type_en or project.visa_type or '').strip()}".strip()
            
            # 解析申请费用，提取数字部分
            selling_price = 0
            if types_info and types_info.fee:
                try:
                    # 尝试从费用字符串中提取数字
                    import re
                    fee_match = re.search(r'(\d+(?:\.\d+)?)', types_info.fee)
                    if fee_match:
                        selling_price = float(fee_match.group(1))
                except (ValueError, AttributeError) as e:
                    pass

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
            
            # 与签证REF编辑页字段对齐：
            # - 国家下拉 value = 国家英文名大写（不是固定代码集）
            # - 签证类型下拉 value = 实际签证类型字符串（project.visa_type）
            # - 出发日期 = 项目预估日期
            country_for_ref = (country_name_en or country_name or '').strip().upper()
            visa_type_for_ref = project.visa_type or ''
            departure_for_ref = project.estimated_date.isoformat() if project.estimated_date else ''

            # 把国家持久化到 VisaProject（REF编辑页从 VisaProject 读取国家/签证类型）
            if not (project.country or '').strip() and country_for_ref:
                project.country = country_for_ref

            visa_extra_info = {
                # 新版签证REF页面字段
                'visa_name': visa_name,
                'country': country_for_ref,        # 国家英文名大写，与下拉 value 对齐
                'visa_type': visa_type_for_ref,    # 实际签证类型，与下拉 value 对齐
                'processing_type': 'NORMAL',  # 默认普通处理
                'pax_names': pax_names_list,
                'leader_id': member_id,
                'departure_date': departure_for_ref,
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
                remarks='',  # 不把签证项目的备注带到自动创建的REF
                status='confirmed',
                payment_status='unpaid',
                extra_info=json.dumps(visa_extra_info, ensure_ascii=False)
            )
            db.session.add(ref)
            db.session.flush()  # 获取ref.id
            
            # 更新签证项目的ref_id
            project.ref_id = ref.id

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
        except json.JSONDecodeError:
            document_statuses = []

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
        # 先保存到数据库，获取项目ID用于构建唯一文件夹名
        from App_new.config import Config

        # 临时名称，flush后用项目ID更新
        temp_name = f"{project_name}_{singapore_status}"
        new_project = VisaProject(
            name=temp_name,
            visa_status=visa_status,
            estimated_date=datetime.strptime(estimated_date, '%Y-%m-%d').date()
        )

        new_project.project_folder_name = temp_name
        new_project.visa_type = visa_type_input
        new_project.applicant_name = applicant_name
        new_project.contact_name = request.form.get('contact_name')
        new_project.remarks = request.form.get('remarks')
        new_project.hid_or_serial = hid_or_serial if hid_or_serial else None  # 可为空
        new_project.singapore_status = singapore_status

        db.session.add(new_project)
        db.session.flush()  # 获取项目ID

        # 用项目ID构建唯一文件夹名，避免同名覆盖
        project_file_name = f"{project_name}_{singapore_status}_{new_project.id}"
        new_project.name = project_file_name
        new_project.project_folder_name = project_file_name

        "a 创建项目文件夹"
        visa_folder = Config.VISA_PROJECTS_PATH  # 签证项目文件夹
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
        
        # 保存资料状态数据
        if document_statuses:
            from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
            for status_data in document_statuses:
                is_ready = status_data['is_ready']
                # 确保is_ready是布尔值
                if isinstance(is_ready, str):
                    is_ready = is_ready.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(is_ready, int):
                    is_ready = bool(is_ready)
                elif not isinstance(is_ready, bool):
                    is_ready = False

                new_status = VisaProjectDocumentStatus(
                    project_id=new_project.id,
                    document_name=status_data['document_name'],
                    document_type=status_data['document_type'],
                    is_ready=is_ready,
                    notes=status_data.get('notes', '')
                )
                db.session.add(new_status)

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


@visa_project.route('/update_remarks/<int:project_id>', methods=['POST'])
@csrf.exempt
def update_remarks(project_id):
    """通过AJAX单独更新项目备注信息"""
    try:
        project = VisaProject.query.get_or_404(project_id)

        # 获取备注数据（允许为空，表示清空备注）
        remarks = request.form.get('remarks', '')
        project.remarks = remarks if remarks.strip() else None

        # 保存到数据库
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '备注信息更新成功',
            'remarks': project.remarks or ''
        })

    except Exception as e:
        db.session.rollback()
        error_msg = f"更新备注信息失败: {str(e)}"
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500


@visa_project.route('/edit_remarks/<int:project_id>', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def edit_remarks_page(project_id):
    """备注信息独立编辑页面：GET 显示编辑页，POST 保存后返回项目详情"""
    project = VisaProject.query.get_or_404(project_id)

    if request.method == 'POST':
        try:
            remarks = request.form.get('remarks', '')
            project.remarks = remarks if remarks.strip() else None
            db.session.commit()
            flash('备注信息更新成功', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'更新备注信息失败: {str(e)}', 'error')
        return redirect(url_for('visa_project.visa_detail', project_id=project_id))

    return render_template('business/visa/签证项目管理/visa_remarks_edit.html', project=project)


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
        from App_new.config import Config

        # 根据文件夹类型构建路径
        if folder_type == 'project' and project_folder and visa_type:
            base_folder = Config.VISA_PROJECTS_PATH
            # 首先尝试在签证类型子文件夹中查找
            folder_path = base_folder / visa_type / project_folder
            if not folder_path.exists():
                # 如果不存在，尝试在根目录中查找
                folder_path = base_folder / project_folder

            if not folder_path.exists():
                # 文件夹不存在时自动创建
                try:
                    # 优先在签证类型子文件夹中创建
                    folder_path = base_folder / visa_type / project_folder
                    folder_path.mkdir(parents=True, exist_ok=True)
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

        elif folder_type == 'visa_root':
            # 修改为正确的签证根目录路径
            folder_path = Config.VISA_RESOURCES_PATH
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
        
        # 获取特定身份资料（按项目实际身份查找，而非SHARE）
        if project.singapore_status and project.singapore_status != 'SHARE':
            specific_identity = VisaSingaporeIdentity.query.filter_by(
                identity_zh=project.singapore_status
            ).first()
            if specific_identity:
                specific_doc = VisaDocuments.query.filter_by(
                    visa_type_id=types_info.id,
                    singapore_identity_id=specific_identity.id
                ).first()
                if specific_doc and specific_doc.selected_documents:
                    for doc in specific_doc.selected_documents:
                        template_documents.append({
                            'name': doc.name,
                            'type': 'document',
                            'category': project.singapore_status
                        })

        # 创建新的资料状态记录（已存在的 + 本次已添加的，统一去重，避免重复加载）
        new_statuses = []
        seen_names = set(existing_document_names)
        for doc in template_documents:
            if doc['name'] not in seen_names:
                seen_names.add(doc['name'])
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
        # 获取项目信息
        project = VisaProject.query.get(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

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
                'created_at': f.created_at.strftime('%Y-%m-%d %H:%M') if f.created_at else '',
                'updated_at': f.updated_at.strftime('%Y-%m-%d %H:%M') if f.updated_at else ''
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

        # 生成唯一文件名 - 使用UUID确保文件名唯一，避免中文文件名导致的覆盖问题
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')  # 包含微秒
        # 使用 UUID + 时间戳 + 扩展名，确保文件名绝对唯一
        new_filename = f"{timestamp}_{unique_id}.{file_ext}" if file_ext else f"{timestamp}_{unique_id}"
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


@visa_project.route('/api/files/bulk_download', methods=['POST'])
@login_required
@staff_only
def bulk_download_files():
    """批量下载项目文件（打包为ZIP）"""
    import zipfile
    import tempfile
    from flask import send_file
    from io import BytesIO

    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])

        if not file_ids:
            return jsonify({'success': False, 'message': '请选择要下载的文件'}), 400

        # 获取所有选中的文件
        files = VisaProjectFile.query.filter(VisaProjectFile.id.in_(file_ids)).all()

        if not files:
            return jsonify({'success': False, 'message': '未找到选中的文件'}), 404

        # 检查文件是否都存在
        valid_files = []
        for f in files:
            if os.path.exists(f.file_path):
                valid_files.append(f)

        if not valid_files:
            return jsonify({'success': False, 'message': '选中的文件都不存在'}), 404

        # 创建ZIP文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in valid_files:
                # 使用原始文件名作为ZIP内的文件名
                zf.write(f.file_path, f.file_name)

        memory_file.seek(0)

        # 生成下载文件名
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'visa_files_{timestamp}.zip'

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        current_app.logger.error(f"批量下载文件失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量下载失败: {str(e)}'}), 500


@visa_project.route('/copy_project/<int:project_id>', methods=['POST'])
@login_required
@staff_only
def copy_project(project_id):
    """复制签证项目（不复制HID和REF，会创建新的）"""
    try:
        import shutil
        from App_new.config import Config

        # 获取原项目
        original_project = VisaProject.query.get_or_404(project_id)

        # 生成新的项目文件夹名称
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 去除申请人姓名中的前后空格，避免文件夹名称问题
        applicant_name = (original_project.applicant_name or '').strip()
        new_folder_name = f"{original_project.visa_type}_COPY_{timestamp}_{applicant_name}"

        # 创建新项目文件夹
        new_project_folder = Config.VISA_PROJECTS_PATH / new_folder_name
        os.makedirs(new_project_folder, exist_ok=True)
        current_app.logger.info(f"创建新项目文件夹: {new_project_folder}")

        # 复制原项目文件夹中的文件到新文件夹
        original_folder_name = original_project.project_folder_name or original_project.name
        original_project_folder = Config.VISA_PROJECTS_PATH / original_folder_name

        files_copied = 0
        if original_project_folder.exists():
            for file in original_project_folder.iterdir():
                if file.is_file():
                    dst_path = new_project_folder / file.name
                    shutil.copy2(file, dst_path)
                    files_copied += 1
                    current_app.logger.info(f"复制文件: {file.name}")
            current_app.logger.info(f"共复制 {files_copied} 个文件")
        else:
            # 如果原项目文件夹不存在，从资源文件夹复制模板文件
            current_app.logger.warning(f"原项目文件夹不存在: {original_project_folder}，尝试从资源文件夹复制")
            visa_type = original_project.visa_type
            singapore_status = original_project.singapore_status or 'PR'

            source_path = Config.VISA_RESOURCES_PATH / visa_type
            share_path = source_path / '共用资料'
            id_path = source_path / singapore_status

            for file_path in [share_path, id_path]:
                if file_path.exists():
                    for file in file_path.iterdir():
                        if file.is_file():
                            dst_path = new_project_folder / file.name
                            shutil.copy2(file, dst_path)
                            files_copied += 1
            current_app.logger.info(f"从资源文件夹复制了 {files_copied} 个文件")

        # 创建新项目（复制基本信息，不复制HID和REF相关字段）
        new_project = VisaProject(
            name=new_folder_name,
            visa_status='待递交'  # 新项目默认为待递交状态
        )

        # 复制基本字段
        new_project.project_folder_name = new_folder_name
        new_project.visa_type = original_project.visa_type
        new_project.applicant_name = applicant_name  # 使用去除空格后的姓名
        new_project.contact_name = (original_project.contact_name or '').strip()
        new_project.singapore_status = original_project.singapore_status
        new_project.remarks = f"[复制自项目ID:{original_project.id}] {original_project.remarks or ''}"
        new_project.estimated_date = None  # 预估日期不复制，需要重新设置

        # 以下字段不复制，保持为空（会创建新的HID和REF）
        # new_project.hid_or_serial = None
        # new_project.header_id = None
        # new_project.ref_id = None

        db.session.add(new_project)
        db.session.commit()

        current_app.logger.info(f"成功复制项目 {original_project.id} -> {new_project.id}")

        return jsonify({
            'success': True,
            'message': f'项目复制成功，已复制 {files_copied} 个文件',
            'new_project_id': new_project.id
        })

    except Exception as e:
        current_app.logger.error(f"复制项目失败: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'复制项目失败: {str(e)}'
        }), 500


# ==================== 签证填表坐标管理 ====================

# 目前支持坐标管理的国家(与 visa_form_coordinates.country 对应)
VISA_COORD_COUNTRIES = {
    'korea': '韩国签证',
}

# 国家标识 -> 资源文件夹名(背景图所在 资源/签证/<folder>/source)
VISA_COORD_FOLDERS = {
    'korea': '韩国签证',
}


def _coord_page_image_path(country, page):
    """某国某页背景图的磁盘路径(Form-page-N.jpg)。国家或页码非法时返回 None。

    生成韩国表格时 VisaForm 也读同一批图(逐页 Image.open 后叠字),
    所以上传和读取必须共用这个函数,不能各写一份。
    """
    import re
    from App_new.config import Config

    folder = VISA_COORD_FOLDERS.get(country)
    if not folder:
        return None
    m = re.search(r'(\d+)$', page or '')
    if not m:
        return None
    return os.path.join(Config.PROJECT_ROOT, '资源', '签证', folder, 'source',
                        f'Form-page-{int(m.group(1))}.jpg')


@visa_project.route('/coordinates/page-image/<country>/<page>')
@login_required
@staff_only
def coordinate_page_image(country, page):
    """返回某页填表背景图(Form-page-N.jpg),供坐标编辑器叠加点位"""
    from flask import send_file, abort

    img_path = _coord_page_image_path(country, page)
    if not img_path or not os.path.exists(img_path):
        abort(404)
    return send_file(img_path)


@visa_project.route('/coordinates/page-images/export')
@login_required
@staff_only
def coordinate_page_images_export():
    """把该国全部背景图打包成 zip 下载,便于整套搬到另一台机器。"""
    import re
    import zipfile
    from io import BytesIO
    from flask import send_file
    from App_new.config import Config

    country = request.args.get('country', 'korea')
    folder = VISA_COORD_FOLDERS.get(country)
    if not folder:
        return jsonify({'success': False, 'message': f'不支持的国家: {country}'}), 400

    source_dir = os.path.join(Config.PROJECT_ROOT, '资源', '签证', folder, 'source')
    images = []
    if os.path.isdir(source_dir):
        for name in os.listdir(source_dir):
            m = re.fullmatch(r'Form-page-(\d+)\.jpg', name)
            if m:
                images.append((int(m.group(1)), name))
    images.sort()

    if not images:
        return jsonify({'success': False, 'message': f'{country} 还没有任何背景图可导出'}), 404

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for _, name in images:
            zf.write(os.path.join(source_dir, name), arcname=name)
    buf.seek(0)

    filename = f"{country}_page_images_{datetime.now().strftime('%Y%m%d')}.zip"
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name=filename)


@visa_project.route('/coordinates/page-image/<country>/<page>', methods=['POST'])
@login_required
@staff_only
def coordinate_page_image_upload(country, page):
    """上传某页背景图。统一转存为 Form-page-N.jpg,旧图自动备份。

    背景图不入 Git(资源/ 被忽略),换服务器后需要在本页重新上传。
    """
    img_path = _coord_page_image_path(country, page)
    if not img_path:
        return jsonify({'success': False, 'message': f'不支持的国家或页码: {country}/{page}'}), 400

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('jpg', 'jpeg', 'png'):
        return jsonify({'success': False, 'message': f'背景图需 jpg/jpeg/png 格式,当前为 .{ext}'}), 400

    try:
        from PIL import Image, UnidentifiedImageError
        try:
            image = Image.open(file.stream)
            image.load()  # 提前触发解码,坏图在这里就炸,而不是写盘写到一半
        except (UnidentifiedImageError, OSError) as e:
            return jsonify({'success': False, 'message': f'不是有效的图片文件: {e}'}), 400

        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        # 旧图先备份,误传能找回来
        backup_name = None
        if os.path.exists(img_path):
            backup_name = f"{os.path.basename(img_path)}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(img_path, os.path.join(os.path.dirname(img_path), backup_name))

        # PNG 可能带透明通道,JPEG 存不了 alpha,统一转 RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(img_path, 'JPEG', quality=92)

        current_app.logger.info(f'背景图上传 {country}/{page}: {img_path} (备份 {backup_name})')
        return jsonify({
            'success': True,
            'message': f'{page} 背景图已更新 ({image.width}×{image.height})',
            'width': image.width,
            'height': image.height,
            'backup': backup_name,
        })
    except Exception as e:
        current_app.logger.error(f'背景图上传失败({country}/{page}): {e}')
        return jsonify({'success': False, 'message': f'上传失败: {e}'}), 500


@visa_project.route('/coordinates')
@login_required
@staff_only
def coordinate_manager():
    """签证填表坐标管理页面(原 坐标列表.xls 已入库)"""
    country = request.args.get('country', 'korea')
    coords = VisaFormCoordinate.query.filter_by(country=country).order_by(
        VisaFormCoordinate.page.asc(), VisaFormCoordinate.id.asc()
    ).all()
    # 按页码分组,方便模板展示
    pages = {}
    for c in coords:
        pages.setdefault(c.page, []).append(c)
    return render_template(
        'business/visa/签证项目管理/coordinate_manager.html',
        country=country,
        country_name=VISA_COORD_COUNTRIES.get(country, country),
        countries=VISA_COORD_COUNTRIES,
        pages=pages,
        total=len(coords)
    )


@visa_project.route('/coordinates/save', methods=['POST'])
@login_required
@staff_only
def coordinate_save():
    """更新单条坐标"""
    try:
        data = request.get_json(silent=True) or request.form
        coord_id = data.get('id')
        coord = VisaFormCoordinate.query.get_or_404(int(coord_id))

        coord.page = (data.get('page') or coord.page).strip()
        coord.seq = (data.get('seq') or coord.seq).strip()
        coord.coord_x = int(data.get('coord_x'))
        coord.coord_y = int(data.get('coord_y'))
        coord.label = (data.get('label') or '').strip() or None
        coord.coord_type = (data.get('coord_type') or '').strip() or None
        coord.type_note = (data.get('type_note') or '').strip() or None

        db.session.commit()
        return jsonify({'success': True, 'message': '保存成功', 'coord': coord.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@visa_project.route('/coordinates/add', methods=['POST'])
@login_required
@staff_only
def coordinate_add():
    """新增一条坐标"""
    try:
        data = request.get_json(silent=True) or request.form
        country = (data.get('country') or 'korea').strip()
        seq = (data.get('seq') or '').strip()
        page = (data.get('page') or '').strip()
        if not seq or not page:
            return jsonify({'success': False, 'message': '页码和坐标序列不能为空'}), 400

        # 校验 (country, seq) 唯一
        exists = VisaFormCoordinate.query.filter_by(country=country, seq=seq).first()
        if exists:
            return jsonify({'success': False, 'message': f'坐标序列 "{seq}" 已存在'}), 400

        coord = VisaFormCoordinate(
            country=country,
            page=page,
            seq=seq,
            coord_x=int(data.get('coord_x') or 0),
            coord_y=int(data.get('coord_y') or 0),
            label=(data.get('label') or '').strip() or None,
            coord_type=(data.get('coord_type') or '').strip() or None,
            type_note=(data.get('type_note') or '').strip() or None,
        )
        db.session.add(coord)
        db.session.commit()
        return jsonify({'success': True, 'message': '新增成功', 'coord': coord.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'新增失败: {str(e)}'}), 500


@visa_project.route('/coordinates/delete/<int:coord_id>', methods=['POST'])
@login_required
@staff_only
def coordinate_delete(coord_id):
    """删除一条坐标"""
    try:
        coord = VisaFormCoordinate.query.get_or_404(coord_id)
        db.session.delete(coord)
        db.session.commit()
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


# ---------------- 坐标导出 / 导入 ----------------
# 坐标只存数据库(visa_form_coordinates),不再依赖 资源/ 下的 坐标列表.xls。
# 本地改好坐标 → 导出 JSON → 在服务器导入,即可把本地数据同步上去。

# 原 坐标列表.xls 的列名 → 模型字段,导入时兼容这套老表头
COORD_XLS_COLUMNS = {
    'PAGE': 'page',
    '坐标序列': 'seq',
    '坐标X': 'coord_x',
    '坐标Y': 'coord_y',
    '坐标说明': 'label',
    '坐标类型': 'coord_type',
    '类型说明': 'type_note',
}


def _coord_backup_dir():
    from App_new.config import Config
    path = os.path.join(Config.PROJECT_ROOT, 'backups', 'visa_coordinates')
    os.makedirs(path, exist_ok=True)
    return path


def _dump_coords(country):
    """导出该国家的坐标为可直接回灌的记录列表(不含 id/country)。"""
    rows = VisaFormCoordinate.query.filter_by(country=country).order_by(
        VisaFormCoordinate.page.asc(), VisaFormCoordinate.id.asc()
    ).all()
    return [{
        'page': c.page,
        'seq': c.seq,
        'coord_x': c.coord_x,
        'coord_y': c.coord_y,
        'label': c.label,
        'coord_type': c.coord_type,
        'type_note': c.type_note,
    } for c in rows]


def _clean_str(value):
    """Excel 的空值会是 NaN,统一收敛成 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text.lower() != 'nan' else None


def _parse_coord_file(file_storage):
    """解析上传的坐标文件,返回规范化记录列表。校验不通过抛 ValueError。

    支持 .json(本页导出的格式)与 .xls/.xlsx(原 坐标列表.xls 的列名)。
    """
    filename = (file_storage.filename or '').lower()
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''

    if ext == 'json':
        try:
            # utf-8-sig 兼容 Windows 记事本存出来的 BOM
            raw = json.loads(file_storage.read().decode('utf-8-sig'))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f'JSON 无法解析: {e}')
        if not isinstance(raw, list):
            raise ValueError('JSON 根节点必须是数组')
        records = raw
    elif ext in ('xls', 'xlsx'):
        import pandas as pd
        df = pd.read_excel(file_storage, sheet_name=0)
        missing = [c for c in ('PAGE', '坐标序列', '坐标X', '坐标Y') if c not in df.columns]
        if missing:
            raise ValueError(f'Excel 缺少必需列: {"、".join(missing)}')
        records = []
        for _, row in df.iterrows():
            records.append({
                field: row.get(col)
                for col, field in COORD_XLS_COLUMNS.items() if col in df.columns
            })
    else:
        raise ValueError(f'不支持的格式 ".{ext}",请上传 .json / .xls / .xlsx')

    cleaned = []
    seen = set()
    for idx, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            raise ValueError(f'第 {idx} 行不是对象')
        page = _clean_str(rec.get('page'))
        seq = _clean_str(rec.get('seq'))
        if not page or not seq:
            continue  # 母版里的分隔空行,跳过
        if seq in seen:
            raise ValueError(f'坐标序列 "{seq}" 在文件里重复(第 {idx} 行),(国家, 序列) 必须唯一')
        seen.add(seq)
        try:
            coord_x = int(float(rec.get('coord_x') or 0))
            coord_y = int(float(rec.get('coord_y') or 0))
        except (TypeError, ValueError):
            raise ValueError(
                f'第 {idx} 行(序列 {seq}) 坐标不是数字: '
                f'X={rec.get("coord_x")!r} Y={rec.get("coord_y")!r}'
            )
        cleaned.append({
            'page': page,
            'seq': seq,
            'coord_x': coord_x,
            'coord_y': coord_y,
            'label': _clean_str(rec.get('label')),
            'coord_type': _clean_str(rec.get('coord_type')),
            'type_note': _clean_str(rec.get('type_note')),
        })

    if not cleaned:
        raise ValueError('文件里没有有效的坐标行')
    return cleaned


@visa_project.route('/coordinates/export')
@login_required
@staff_only
def coordinate_export():
    """把某国家的坐标导出成 JSON 文件下载(可原样导入回来)。"""
    from flask import Response

    country = request.args.get('country', 'korea')
    if country not in VISA_COORD_COUNTRIES:
        return jsonify({'success': False, 'message': f'不支持的国家: {country}'}), 400

    records = _dump_coords(country)
    filename = f"{country}_coordinates_{datetime.now().strftime('%Y%m%d')}.json"
    return Response(
        json.dumps(records, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@visa_project.route('/coordinates/import', methods=['POST'])
@login_required
@staff_only
def coordinate_import():
    """整国覆盖导入坐标:先备份现有数据,再在一个事务里清空并写入。

    覆盖语义 = 导入后该国家的坐标与文件完全一致,文件里没有的行会被删除。
    """
    country = (request.form.get('country') or 'korea').strip()
    if country not in VISA_COORD_COUNTRIES:
        return jsonify({'success': False, 'message': f'不支持的国家: {country}'}), 400

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    try:
        records = _parse_coord_file(file)
    except ValueError as e:
        return jsonify({'success': False, 'message': f'文件解析失败: {e}'}), 400
    except Exception as e:
        current_app.logger.error(f'坐标文件解析异常({country}): {e}')
        return jsonify({'success': False, 'message': f'文件解析失败: {e}'}), 400

    # 覆盖是破坏性的,先把现有数据落盘,出事能手工回灌。
    # 时间戳只到秒,同一秒内的两次导入会撞名,加序号兜底,绝不覆盖已有备份。
    backup_dir = _coord_backup_dir()
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'{country}_{stamp}.json'
    dup = 1
    while os.path.exists(os.path.join(backup_dir, backup_name)):
        dup += 1
        backup_name = f'{country}_{stamp}_{dup}.json'
    backup_path = os.path.join(backup_dir, backup_name)
    old_records = _dump_coords(country)
    try:
        with open(backup_path, 'w', encoding='utf-8') as fp:
            json.dump(old_records, fp, ensure_ascii=False, indent=2)
    except Exception as e:
        current_app.logger.error(f'坐标备份失败({country}): {e}')
        return jsonify({'success': False, 'message': f'备份失败,已中止导入: {e}'}), 500

    try:
        deleted = VisaFormCoordinate.query.filter_by(country=country).delete()
        for rec in records:
            db.session.add(VisaFormCoordinate(country=country, **rec))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'坐标导入失败({country}): {e}')
        return jsonify({'success': False, 'message': f'导入失败,已回滚(原数据未改动): {e}'}), 500

    current_app.logger.info(
        f'坐标导入 {country}: 覆盖 {deleted} 条 → 写入 {len(records)} 条,备份于 {backup_path}')
    return jsonify({
        'success': True,
        'message': f'导入成功:原有 {deleted} 条已覆盖为 {len(records)} 条(备份 {backup_name})',
        'deleted': deleted,
        'imported': len(records),
        'backup': backup_name,
    })