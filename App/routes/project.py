from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from ..models.Project import Project, ProjectRef, ProjectEO
from ..models.Suppliers import Supplier
from ..models.BusinessType import BusinessType
from ..exts import db
from datetime import datetime
from sqlalchemy import func
import traceback  # 添加traceback模块

projects = Blueprint('projects', __name__)

@projects.route('/create', methods=['GET'])
def confirm_create():
    """显示确认创建项目的页面"""
    generated_hid = Project.generate_hid()
    return render_template('projects/confirm_create.html',
                         generated_hid=generated_hid)

@projects.route('/create/<hid>', methods=['GET', 'POST'])
def create_project(hid):
    """创建新项目的详细信息页面"""
    if request.method == 'POST':
        try:
            # 处理日期字段
            start_date = datetime.strptime(request.form.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date', start_date.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            
            # 处理金额字段
            total_amount = request.form.get('total_amount')
            paid_amount = request.form.get('paid_amount')
            
            try:
                total_amount = float(total_amount) if total_amount else None
                paid_amount = float(paid_amount) if paid_amount else None
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '金额格式无效'
                }), 400
            
            # 创建项目
            new_project = Project(
                hid=hid,  # 使用传入的HID
                project_name=request.form['project_name'],
                name=request.form.get('name'),
                description=request.form.get('description'),
                status=request.form.get('status', 'draft'),
                start_date=start_date,
                end_date=end_date,
                
                # 客户信息
                client_name=request.form['client_name'],
                customer_phone=request.form.get('customer_phone'),
                customer_email=request.form.get('customer_email'),
                customer_id_type=request.form.get('customer_id_type'),
                customer_id_number=request.form.get('customer_id_number'),
                customer_company=request.form.get('customer_company'),
                customer_contact_person=request.form.get('customer_contact_person'),
                
                # 财务信息
                total_amount=total_amount,
                paid_amount=paid_amount
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
    # 检查HID是否已存在
    existing_project = Project.query.filter_by(hid=hid).first()
    if existing_project:
        return redirect(url_for('projects.list_projects'))
        
    # 获取必要的数据
    supplier_types = Supplier.get_supplier_types()
    supplier_type_map = Supplier.SUPPLIER_TYPE_MAP
    suppliers = [supplier.to_dict() for supplier in Supplier.query.filter_by(status='active').all()]
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
    
    return render_template('projects/create_project.html',
                         generated_hid=hid,
                         now=datetime.now(),
                         supplier_types=supplier_types,
                         supplier_type_map=supplier_type_map,
                         suppliers=suppliers,
                         business_types=business_types)

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
    business_types = BusinessType.query.filter_by(is_active=True).order_by(BusinessType.sort_order).all()
    suppliers = Supplier.query.filter_by(status='active').order_by(Supplier.name).all()
    return render_template('projects/view_project.html', 
                         project=project,
                         business_types=business_types,
                         suppliers=suppliers)

@projects.route('/<int:project_id>/add_ref', methods=['POST'])
def add_ref(project_id):
    """添加新的REF"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': '无效的请求'}), 400

    try:
        project = Project.query.get_or_404(project_id)
        
        # 获取并验证必填字段
        ref_type_id = request.form.get('ref_type_id')
        if not ref_type_id:
            return jsonify({
                'success': False,
                'message': 'REF类型不能为空'
            }), 400
            
        business_type = BusinessType.query.get(ref_type_id)
        if not business_type:
            return jsonify({
                'success': False,
                'message': f'无效的REF类型ID: {ref_type_id}'
            }), 400
        
        description = request.form.get('description')
        if not description:
            return jsonify({
                'success': False,
                'message': '描述不能为空'
            }), 400
        
        # 生成REF编号
        try:
            # 获取该项目的所有REF数量
            ref_count = ProjectRef.query.filter_by(project_id=project.id).count()
            ref_number = f"{project.hid}-R{str(ref_count + 1).zfill(2)}"
        except Exception as e:
            print("Error generating REF number:", str(e))
            return jsonify({
                'success': False,
                'message': f'生成REF编号失败: {str(e)}'
            }), 400
        
        # 处理供应商ID
        supplier_id = request.form.get('supplier_id')
        if supplier_id:
            try:
                supplier_id = int(supplier_id)
                supplier = Supplier.query.get(supplier_id)
                if not supplier:
                    return jsonify({
                        'success': False,
                        'message': f'无效的供应商ID: {supplier_id}'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '供应商ID必须是有效的整数'
                }), 400
        
        # 处理价格字段
        selling_price = request.form.get('selling_price')
        cost_price = request.form.get('cost_price')
        try:
            selling_price = float(selling_price) if selling_price else 0.0
            cost_price = float(cost_price) if cost_price else 0.0
        except ValueError:
            return jsonify({
                'success': False,
                'message': '价格格式无效'
            }), 400
        
        # 处理日期字段
        expected_delivery_date = request.form.get('expected_delivery_date')
        if expected_delivery_date:
            try:
                expected_delivery_date = datetime.strptime(expected_delivery_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '预计交付日期格式无效'
                }), 400
        
        # 创建新的REF
        new_ref = ProjectRef(
            project_id=project.id,
            ref_number=ref_number,
            name=request.form.get('name'),
            ref_type_id=business_type.id,
            description=description,
            supplier_id=supplier_id,
            supplier_contact=request.form.get('supplier_contact'),
            supplier_phone=request.form.get('supplier_phone'),
            selling_price=selling_price,
            cost_price=cost_price,
            currency=request.form.get('currency', 'SGD'),
            expected_delivery_date=expected_delivery_date,
            remarks=request.form.get('remarks'),
            status=request.form.get('status', 'draft'),
            payment_status=request.form.get('payment_status', 'unpaid')
        )
        
        db.session.add(new_ref)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'REF创建成功',
            'ref': {
                'id': new_ref.id,
                'ref_number': new_ref.ref_number
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_details = traceback.format_exc()
        print("Error creating REF:", error_details)
        return jsonify({
            'success': False,
            'message': f'创建REF失败: {str(e)}',
            'details': error_details
        }), 400

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