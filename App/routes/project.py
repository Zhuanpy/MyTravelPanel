from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from ..models.Project import Project, ProjectRef, ProjectEO
from ..models.Suppliers import Supplier
from ..models.BusinessType import BusinessType
from ..exts import db
from datetime import datetime
from sqlalchemy import func
import traceback  # 添加traceback模块

projects = Blueprint('projects', __name__)

@projects.route('/create', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date', start_date.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            
            # 创建项目
            new_project = Project(
                hid=request.form['hid'],
                project_name=request.form['project_name'],
                client_name=request.form['client_name'],
                description=request.form.get('description'),
                status=request.form.get('project_status', 'draft'),
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(new_project)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'hid': new_project.hid,
                'redirect': url_for('projects.create_project_ref', hid=new_project.hid)
            })
            
        except Exception as e:
            db.session.rollback()
            error_details = traceback.format_exc()
            print("Error details:", error_details)
            return jsonify({
                'success': False,
                'error': str(e),
                'details': error_details
            }), 400

    # GET请求处理
    generated_hid = Project.generate_hid()
    return render_template('projects/create_project.html',
                         generated_hid=generated_hid,
                         now=datetime.now())

@projects.route('/<hid>/create_ref', methods=['GET', 'POST'])
def create_project_ref(hid):
    project = Project.query.filter_by(hid=hid).first_or_404()
    
    if request.method == 'POST':
        try:
            # 处理REF
            ref_numbers = request.form.getlist('ref_number[]')
            ref_type_ids = request.form.getlist('ref_type_id[]')
            ref_descriptions = request.form.getlist('ref_description[]')
            supplier_ids = request.form.getlist('supplier_id[]')
            selling_amounts = request.form.getlist('selling[]')
            cost_amounts = request.form.getlist('cost[]')
            
            for i in range(len(ref_numbers)):
                new_ref = ProjectRef(
                    project_id=project.id,
                    ref_number=ref_numbers[i],
                    ref_type_id=ref_type_ids[i],
                    description=ref_descriptions[i],
                    supplier_id=supplier_ids[i],
                    selling_amount=selling_amounts[i],
                    cost_amount=cost_amounts[i]
                )
                db.session.add(new_ref)
                db.session.flush()  # 获取新REF ID

                # 处理EO
                eo_numbers = request.form.getlist(f'eo_number_{i}[]')
                eo_types = request.form.getlist(f'eo_type_{i}[]')
                eo_suppliers = request.form.getlist(f'eo_supplier_{i}[]')
                eo_selling = request.form.getlist(f'eo_selling_{i}[]')
                eo_cost = request.form.getlist(f'eo_cost_{i}[]')
                eo_remarks = request.form.getlist(f'eo_remark_{i}[]')
                
                for j in range(len(eo_numbers)):
                    new_eo = ProjectEO(
                        ref_id=new_ref.id,
                        eo_number=eo_numbers[j],
                        supplier_type=eo_types[j],
                        supplier_id=eo_suppliers[j],
                        selling_amount=eo_selling[j],
                        cost_amount=eo_cost[j],
                        remarks=eo_remarks[j]
                    )
                    db.session.add(new_eo)

            db.session.commit()
            return jsonify({
                'success': True,
                'redirect': url_for('projects.view_project', project_id=project.id)
            })

        except Exception as e:
            db.session.rollback()
            error_details = traceback.format_exc()
            print("Error details:", error_details)
            return jsonify({
                'success': False,
                'error': str(e),
                'details': error_details
            }), 400

    # GET请求处理
    supplier_types = Supplier.get_supplier_types()
    supplier_type_map = Supplier.SUPPLIER_TYPE_MAP
    suppliers = [supplier.to_dict() for supplier in Supplier.query.filter_by(status='active').all()]
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    return render_template('projects/create_project_ref.html',
                         project=project,
                         supplier_types=supplier_types,
                         supplier_type_map=supplier_type_map,
                         suppliers=suppliers,
                         business_types=business_types)

@projects.route('/<int:project_id>')
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('projects/view_project.html', project=project)

@projects.route('/')
def list_projects():
    status = request.args.get('status')
    query = Project.query

    if status:
        query = query.filter(Project.status == status)
    
    projects = query.order_by(Project.created_at.desc()).all()
    return render_template('projects/list_projects.html', projects=projects)

@projects.route('/statistics')
def project_statistics():
    # 获取项目总数
    total_projects = Project.query.count()
    
    # 按状态统计项目数量
    status_stats = db.session.query(
        Project.status,
        func.count(Project.id)
    ).group_by(Project.status).all()
    
    # 按月统计项目数量（最近12个月）
    monthly_stats = db.session.query(
        func.date_format(Project.created_at, '%Y-%m'),
        func.count(Project.id)
    ).group_by(
        func.date_format(Project.created_at, '%Y-%m')
    ).order_by(
        func.date_format(Project.created_at, '%Y-%m').desc()
    ).limit(12).all()
    
    # 统计REF类型分布
    ref_type_stats = db.session.query(
        BusinessType.name,
        func.count(ProjectRef.id)
    ).join(ProjectRef.ref_type).group_by(BusinessType.name).all()
    
    # 统计供应商类型分布
    supplier_type_stats = db.session.query(
        ProjectEO.supplier_type,
        func.count(ProjectEO.id)
    ).group_by(ProjectEO.supplier_type).all()
    
    return render_template('projects/statistics.html',
                         total_projects=total_projects,
                         status_stats=status_stats,
                         monthly_stats=monthly_stats,
                         ref_type_stats=ref_type_stats,
                         supplier_type_stats=supplier_type_stats)

@projects.route('/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        try:
            project.project_name = request.form['project_name']
            project.client_name = request.form['client_name']
            project.description = request.form.get('description')
            project.status = request.form.get('project_status')
            
            db.session.commit()
            return redirect(url_for('projects.view_project', project_id=project.id))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    supplier_types = Supplier.get_supplier_types()
    supplier_type_map = Supplier.SUPPLIER_TYPE_MAP
    suppliers = [supplier.to_dict() for supplier in Supplier.query.filter_by(status='active').all()]
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()

    return render_template('projects/edit_project.html',
                         project=project,
                         supplier_types=supplier_types,
                         supplier_type_map=supplier_type_map,
                         suppliers=suppliers,
                         business_types=business_types)

@projects.route('/generate_ref_number/<project_hid>', methods=['GET'])
def generate_ref_number(project_hid):
    """生成新的REF编号"""
    try:
        print(f"Generating REF number for project HID: {project_hid}")
        ref_number = ProjectRef.generate_ref_number(project_hid)
        print(f"Generated REF number: {ref_number}")
        return jsonify({'ref_number': ref_number})
    except Exception as e:
        error_details = traceback.format_exc()
        print("Error generating REF number:", error_details)
        return jsonify({
            'error': str(e),
            'details': error_details
        }), 400 