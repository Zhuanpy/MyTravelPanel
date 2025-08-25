from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from App_new.business.projects.models.ref import ProjectRef
from App_new.business.projects.models.eo import ProjectEO
from App_new.exts import csrf, db
from App_new.business.projects.forms.eo_forms import ProjectEOForm
from App_new.utils.decorators import staff_only, admin_only
import json

project_eo = Blueprint('project_eo', __name__)

@project_eo.route('/create/<int:ref_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def create_eo(ref_id):
    """创建EO"""
    ref = ProjectRef.query.get_or_404(ref_id)
    form = ProjectEOForm()
    form.ref_id.data = ref_id
    
    # 确保供应商选项已加载
    form._load_choices()
    
    if form.validate_on_submit():
        try:
            eo_number = ProjectEO.generate_eo_number()
            eo = ProjectEO(
                ref_id=ref.id,
                eo_number=eo_number,
                name=form.name.data,
                supplier_type=form.supplier_type.data,
                supplier_id=form.supplier_id.data,
                external_system=form.external_system.data,
                external_status=form.external_status.data,
                external_reference=form.external_reference.data,
                amount=form.amount.data,
                currency=form.currency.data,
                remarks=form.remarks.data,
                status=form.status.data
            )
            db.session.add(eo)
            db.session.commit()
            flash('EO子明细创建成功！', 'success')
            return redirect(url_for('project_ref.ref_detail', ref_id=ref.id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    # 预填充EO编号
    eo_number = ProjectEO.generate_eo_number()
    form.eo_number.data = eo_number
    
    # 从REF中自动获取和预填充数据
    if request.method == 'GET':
        # 预填充EO名称（使用REF名称）
        if not form.name.data:
            form.name.data = ref.name or ref.description or f"{ref.ref_type.name if ref.ref_type else 'REF'}订单"
        
        # 预填充供应商类型（根据REF类型推断）
        if not form.supplier_type.data:
            if ref.ref_type:
                ref_type_name = ref.ref_type.name
                if '机票' in ref_type_name:
                    form.supplier_type.data = 'flight'
                elif '酒店' in ref_type_name:
                    form.supplier_type.data = 'hotel'
                elif '签证' in ref_type_name:
                    form.supplier_type.data = 'visa'
                elif '交通' in ref_type_name or '用车' in ref_type_name:
                    form.supplier_type.data = 'transport'
                elif '旅游' in ref_type_name or '团' in ref_type_name:
                    form.supplier_type.data = 'local_operator'
                elif '保险' in ref_type_name:
                    form.supplier_type.data = 'other'
                else:
                    form.supplier_type.data = 'other'
        
        # 预填充供应商ID（使用REF的供应商）
        if not form.supplier_id.data and ref.supplier_id:
            form.supplier_id.data = ref.supplier_id
        
        # 预填充金额（使用REF的成本价格）
        if not form.amount.data and ref.cost_price:
            form.amount.data = ref.cost_price
        
        # 预填充货币（使用REF的货币）
        if not form.currency.data and ref.currency:
            form.currency.data = ref.currency
        elif not form.currency.data:
            form.currency.data = 'SGD'  # 默认货币
        
        # 预填充备注（使用REF的备注）
        if not form.remarks.data and ref.remarks:
            form.remarks.data = ref.remarks
        
        # 预填充状态（默认为已确认）
        if not form.status.data:
            form.status.data = 'confirmed'
    
    return render_template('business/projects/project_eo/create_eo.html',
                           form=form, ref=ref, eo_number=eo_number)

@project_eo.route('/<int:eo_id>')
def eo_detail(eo_id):
    """EO详情页面"""
    eo = ProjectEO.query.get_or_404(eo_id)
    return render_template('business/projects/project_eo/eo_detail.html', eo=eo)

@project_eo.route('/<int:eo_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_eo(eo_id):
    """编辑EO"""
    eo = ProjectEO.query.get_or_404(eo_id)
    form = ProjectEOForm(obj=eo)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(eo)
            db.session.commit()
            return redirect(url_for('project_eo.eo_detail', eo_id=eo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('business/projects/project_eo/edit_eo.html', form=form, eo=eo)

@project_eo.route('/quick_create/<int:ref_id>', methods=['POST'])
@csrf.exempt
def quick_create_eo(ref_id):
    """一键生成EO - API接口"""
    try:
        ref = ProjectRef.query.get_or_404(ref_id)
        
        # 检查REF是否已经有EO
        existing_eo = ProjectEO.query.filter_by(ref_id=ref.id).first()
        if existing_eo:
            return jsonify({
                'success': False,
                'message': f'REF {ref.ref_number} 已经存在EO编号 {existing_eo.eo_number}'
            }), 400
        
        # 根据REF类型推断供应商类型
        supplier_type = 'other'
        if ref.ref_type:
            ref_type_name = ref.ref_type.name
            if '机票' in ref_type_name:
                supplier_type = 'flight'
            elif '酒店' in ref_type_name:
                supplier_type = 'hotel'
            elif '签证' in ref_type_name:
                supplier_type = 'visa'
            elif '交通' in ref_type_name or '用车' in ref_type_name:
                supplier_type = 'transport'
            elif '旅游' in ref_type_name or '团' in ref_type_name:
                supplier_type = 'local_operator'
            elif '保险' in ref_type_name:
                supplier_type = 'other'
        
        # 创建EO
        eo = ProjectEO(
            ref_id=ref.id,
            name=ref.name or ref.description or f"{ref.ref_type.name if ref.ref_type else 'REF'}订单",
            supplier_type=supplier_type,
            supplier_id=ref.supplier_id or 1,  # 如果没有供应商，使用默认供应商
            external_system=None,
            external_status=None,
            external_reference=None,
            amount=ref.cost_price or 0,
            currency=ref.currency or 'SGD',
            remarks=ref.remarks,
            status='confirmed'
        )
        
        # 先保存获取ID
        db.session.add(eo)
        db.session.flush()  # 获取ID但不提交
        
        # 使用ID生成EO编号
        eo.eo_number = f'E{str(eo.id).zfill(3)}'
        
        # 提交事务
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'EO {eo.eo_number} 创建成功！',
            'eo_number': eo.eo_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建失败：{str(e)}'
        }), 500
