import os
from datetime import datetime
from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app, Response
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from ..exts import db, csrf
from ..models.Product.PackageBudget import BudgetHeader, BudgetItem
import urllib.parse


# 创建蓝图
package_budget = Blueprint('package_budget', __name__, url_prefix='/package_budget')


@package_budget.route('/')
@package_budget.route('/list')
def list_budgets():
    """预算单列表页面"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        is_template_filter = request.args.get('is_template', '')
        
        # 构建查询
        query = BudgetHeader.query
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    BudgetHeader.package_name.ilike(f'%{search}%'),
                    BudgetHeader.remarks.ilike(f'%{search}%'),
                    BudgetHeader.created_by.ilike(f'%{search}%')
                )
            )
        
        # 状态过滤
        if status_filter:
            query = query.filter(BudgetHeader.status == status_filter)
        
        # 类型过滤
        if is_template_filter != '':
            is_template_bool = is_template_filter == '1'
            query = query.filter(BudgetHeader.is_template == is_template_bool)
        
        # 排序
        query = query.order_by(BudgetHeader.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        budgets = pagination.items
        
        return render_template('package/budget/list.html', 
                             budgets=budgets, 
                             pagination=pagination)
    
    except Exception as e:
        current_app.logger.error(f"Error in list_budgets: {e}")
        flash('获取预算单列表时发生错误', 'error')
        return render_template('package/budget/list.html', budgets=[], pagination=None)


@package_budget.route('/create', methods=['GET', 'POST'])
@csrf.exempt
def create():
    """创建新预算单"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            package_name = request.form.get('package_name', '').strip()
            adult_count = request.form.get('adult_count', type=int)
            child_count = request.form.get('child_count', type=int) or 0
            currency = request.form.get('currency', 'SGD')
            status = request.form.get('status', 'draft')
            is_template = request.form.get('is_template') == '1'
            remarks = request.form.get('remarks', '').strip()
            
            # 验证必填字段
            if not package_name:
                flash('套餐名称不能为空', 'error')
                return render_template('package/budget/create.html', form=request.form)
            
            if not adult_count or adult_count < 1:
                flash('成人数量必须大于0', 'error')
                return render_template('package/budget/create.html', form=request.form)
            
            # 创建预算单
            budget = BudgetHeader(
                package_name=package_name,
                adult_count=adult_count,
                child_count=child_count,
                currency=currency,
                status=status,
                is_template=is_template,
                remarks=remarks,
                created_by=request.form.get('created_by', 'admin'),  # 可以从session获取当前用户
                created_at=datetime.utcnow()
            )
            
            db.session.add(budget)
            db.session.commit()
            
            flash('预算单创建成功！', 'success')
            return redirect(url_for('package_budget.detail', budget_id=budget.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in create budget: {e}")
            flash('创建预算单时发生数据库错误', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in create budget: {e}")
            flash('创建预算单时发生错误', 'error')
    
    return render_template('package/budget/create.html')


@package_budget.route('/<int:budget_id>')
def detail(budget_id):
    """预算单详情页面"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        
        # 计算分类统计
        category_totals = {}
        adult_total = 0
        child_total = 0
        
        for item in budget.items:
            # 分类统计
            category = item.category or '未分类'
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += item.subtotal or 0
            
            # 计算成人费用
            if item.count_adult_apply:
                adult_count = item.adult_count_override or budget.adult_count
                adult_unit_price = item.adult_unit_price or 0
                adult_total += adult_unit_price * adult_count
            
            # 计算儿童费用
            if item.count_child_apply:
                child_count = item.child_count_override or budget.child_count
                child_unit_price = item.child_unit_price or 0
                child_total += child_unit_price * child_count
        
        return render_template('package/budget/detail.html',
                             budget=budget,
                             category_totals=category_totals,
                             adult_total=adult_total,
                             child_total=child_total)
    
    except Exception as e:
        current_app.logger.error(f"Error in budget detail: {e}")
        flash('获取预算单详情时发生错误', 'error')
        return redirect(url_for('package_budget.list_budgets'))


@package_budget.route('/<int:budget_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit(budget_id):
    """编辑预算单"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        
        if request.method == 'POST':
            # 获取表单数据
            package_name = request.form.get('package_name', '').strip()
            adult_count = request.form.get('adult_count', type=int)
            child_count = request.form.get('child_count', type=int) or 0
            currency = request.form.get('currency', 'SGD')
            status = request.form.get('status', 'draft')
            is_template = request.form.get('is_template') == '1'
            remarks = request.form.get('remarks', '').strip()
            
            # 验证必填字段
            if not package_name:
                flash('套餐名称不能为空', 'error')
                return render_template('package/budget/edit.html', budget=budget)
            
            if not adult_count or adult_count < 1:
                flash('成人数量必须大于0', 'error')
                return render_template('package/budget/edit.html', budget=budget)
            
            # 更新预算单
            budget.package_name = package_name
            budget.adult_count = adult_count
            budget.child_count = child_count
            budget.currency = currency
            budget.status = status
            budget.is_template = is_template
            budget.remarks = remarks
            budget.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('预算单更新成功！', 'success')
            return redirect(url_for('package_budget.detail', budget_id=budget.id))
        
        return render_template('package/budget/edit.html', budget=budget)
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in edit budget: {e}")
        flash('更新预算单时发生数据库错误', 'error')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in edit budget: {e}")
        flash('更新预算单时发生错误', 'error')
    
    return redirect(url_for('package_budget.detail', budget_id=budget_id))


@package_budget.route('/<int:budget_id>/delete', methods=['POST'])
@csrf.exempt
def delete(budget_id):
    """删除预算单"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        
        # 删除关联的项目
        for item in budget.items:
            db.session.delete(item)
        
        # 删除预算单
        db.session.delete(budget)
        db.session.commit()
        
        flash('预算单删除成功！', 'success')
        return jsonify({'success': True})
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in delete budget: {e}")
        return jsonify({'success': False, 'error': '数据库错误'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in delete budget: {e}")
        return jsonify({'success': False, 'error': '删除失败'}), 500


@package_budget.route('/<int:budget_id>/add_item', methods=['POST'])
@csrf.exempt
def add_item(budget_id):
    """添加预算项目"""
    header = BudgetHeader.query.get_or_404(budget_id)
    
    try:
        # 获取表单数据
        category = request.form.get('category', '').strip()
        item_name = request.form.get('item_name', '').strip()
        item_details = request.form.get('item_details', '').strip()
        pricing_method = request.form.get('pricing_method', 'person_based')
        
        # 验证必填字段
        if not category:
            flash('类别不能为空', 'error')
            return redirect(url_for('package_budget.detail', budget_id=budget_id))
        
        if not item_name:
            flash('项目名称不能为空', 'error')
            return redirect(url_for('package_budget.detail', budget_id=budget_id))
        
        # 创建新项目
        item = BudgetItem(
            header_id=budget_id,
            category=category,
            item_name=item_name,
            item_details=item_details,
            pricing_method=pricing_method
        )
        
        # 根据计价方式处理价格数据
        if pricing_method == 'item_based':
            # 模板1：物品计价方式
            item_unit_price = request.form.get('item_unit_price')
            item_quantity = request.form.get('item_quantity', 1)
            
            if item_unit_price and item_quantity:
                item.item_unit_price = float(item_unit_price)
                item.item_quantity = int(item_quantity)
            else:
                flash('物品计价方式需要填写物品单价和件数', 'error')
                return redirect(url_for('package_budget.detail', budget_id=budget_id))
                
        else:
            # 模板2：人均计价方式
            adult_price = request.form.get('adult_price')
            child_price = request.form.get('child_price')
            
            if adult_price:
                item.adult_price = float(adult_price)
            if child_price:
                item.child_price = float(child_price)
                
            if not adult_price and not child_price:
                flash('人均计价方式需要至少填写成人单价或儿童单价', 'error')
                return redirect(url_for('package_budget.detail', budget_id=budget_id))
        
        # 处理人数设置
        item.count_adult_apply = 'count_adult_apply' in request.form
        item.count_child_apply = 'count_child_apply' in request.form
        item.is_optional = 'is_optional' in request.form
        
        # 处理可选的人数覆盖
        adult_count_override = request.form.get('adult_count_override')
        child_count_override = request.form.get('child_count_override')
        
        if adult_count_override:
            item.adult_count_override = int(adult_count_override)
        if child_count_override:
            item.child_count_override = int(child_count_override)
        
        # 处理备注
        remarks = request.form.get('remarks', '').strip()
        if remarks:
            item.remarks = remarks
        
        # 设置排序
        max_order = db.session.query(db.func.max(BudgetItem.sort_order)).filter_by(header_id=budget_id).scalar() or 0
        item.sort_order = max_order + 1
        
        db.session.add(item)
        db.session.commit()
        
        flash('项目添加成功！', 'success')
        
    except ValueError as e:
        flash(f'数据格式错误: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'添加失败: {str(e)}', 'error')
    
    return redirect(url_for('package_budget.detail', budget_id=budget_id))


@package_budget.route('/<int:budget_id>/item/<int:item_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
def edit_item(budget_id, item_id):
    """编辑预算项目"""
    header = BudgetHeader.query.get_or_404(budget_id)
    item = BudgetItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            category = request.form.get('category', '').strip()
            item_name = request.form.get('item_name', '').strip()
            item_details = request.form.get('item_details', '').strip()
            pricing_method = request.form.get('pricing_method', 'person_based')
            
            # 验证必填字段
            if not category:
                flash('类别不能为空', 'error')
                return redirect(url_for('package_budget.edit_item', budget_id=budget_id, item_id=item_id))
            
            if not item_name:
                flash('项目名称不能为空', 'error')
                return redirect(url_for('package_budget.edit_item', budget_id=budget_id, item_id=item_id))
            
            # 更新基本信息
            item.category = category
            item.item_name = item_name
            item.item_details = item_details
            item.pricing_method = pricing_method
            
            # 根据计价方式处理价格数据
            if pricing_method == 'item_based':
                # 模板1：物品计价方式
                item_unit_price = request.form.get('item_unit_price')
                item_quantity = request.form.get('item_quantity', 1)
                
                if item_unit_price and item_quantity:
                    item.item_unit_price = float(item_unit_price)
                    item.item_quantity = int(item_quantity)
                    # 清空人均价格字段
                    item.adult_price = None
                    item.child_price = None
                else:
                    flash('物品计价方式需要填写物品单价和件数', 'error')
                    return redirect(url_for('package_budget.edit_item', budget_id=budget_id, item_id=item_id))
                    
            else:
                # 模板2：人均计价方式
                adult_price = request.form.get('adult_price')
                child_price = request.form.get('child_price')
                
                if adult_price:
                    item.adult_price = float(adult_price)
                else:
                    item.adult_price = None
                    
                if child_price:
                    item.child_price = float(child_price)
                else:
                    item.child_price = None
                    
                if not adult_price and not child_price:
                    flash('人均计价方式需要至少填写成人单价或儿童单价', 'error')
                    return redirect(url_for('package_budget.edit_item', budget_id=budget_id, item_id=item_id))
                
                # 清空物品价格字段
                item.item_unit_price = None
                item.item_quantity = 1
            
            # 处理人数设置
            item.count_adult_apply = 'count_adult_apply' in request.form
            item.count_child_apply = 'count_child_apply' in request.form
            item.is_optional = 'is_optional' in request.form
            
            # 处理可选的人数覆盖
            adult_count_override = request.form.get('adult_count_override')
            child_count_override = request.form.get('child_count_override')
            
            if adult_count_override:
                item.adult_count_override = int(adult_count_override)
            else:
                item.adult_count_override = None
                
            if child_count_override:
                item.child_count_override = int(child_count_override)
            else:
                item.child_count_override = None
            
            # 处理备注
            remarks = request.form.get('remarks', '').strip()
            item.remarks = remarks if remarks else None
            
            db.session.commit()
            flash('项目更新成功！', 'success')
            return redirect(url_for('package_budget.detail', budget_id=budget_id))
            
        except ValueError as e:
            flash(f'数据格式错误: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')
    
    return render_template('package/budget/edit_item.html', budget=header, item=item)


@package_budget.route('/<int:budget_id>/item/<int:item_id>/delete', methods=['POST'])
@csrf.exempt
def delete_item(budget_id, item_id):
    """删除预算项目"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        item = BudgetItem.query.get_or_404(item_id)
        
        if item.header_id != budget_id:
            return jsonify({'success': False, 'error': '项目不属于此预算单'}), 400
        
        # 检查CSRF token（如果使用JSON请求）
        if request.is_json:
            # 从JSON数据中获取CSRF token
            data = request.get_json()
            csrf_token = data.get('csrf_token')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'CSRF token缺失'}), 400
        else:
            # 从表单数据中获取CSRF token
            csrf_token = request.form.get('csrf_token')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'CSRF token缺失'}), 400
        
        db.session.delete(item)
        db.session.commit()
        
        flash('项目删除成功！', 'success')
        return jsonify({'success': True})
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in delete item: {e}")
        return jsonify({'success': False, 'error': '数据库错误'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in delete item: {e}")
        return jsonify({'success': False, 'error': '删除失败'}), 500


@package_budget.route('/<int:budget_id>/duplicate', methods=['POST'])
@csrf.exempt
def duplicate(budget_id):
    """复制预算单"""
    try:
        original_budget = BudgetHeader.query.get_or_404(budget_id)
        
        # 创建新的预算单
        new_budget = BudgetHeader(
            package_name=f"{original_budget.package_name} - 副本",
            adult_count=original_budget.adult_count,
            child_count=original_budget.child_count,
            currency=original_budget.currency,
            status='draft',
            is_template=False,
            remarks=original_budget.remarks,
            created_by=request.form.get('created_by', 'admin'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_budget)
        db.session.flush()  # 获取新预算单的ID
        
        # 复制所有项目
        for original_item in original_budget.items:
            new_item = BudgetItem(
                header_id=new_budget.id,
                category=original_item.category,
                item_name=original_item.item_name,
                adult_price=original_item.adult_price,
                child_price=original_item.child_price,
                total_override=original_item.total_override,
                count_adult_apply=original_item.count_adult_apply,
                count_child_apply=original_item.count_child_apply,
                adult_count_override=original_item.adult_count_override,
                child_count_override=original_item.child_count_override,
                sort_order=original_item.sort_order,
                tax_rate=original_item.tax_rate,
                tax_amount=original_item.tax_amount,
                is_optional=original_item.is_optional,
                remarks=original_item.remarks
            )
            db.session.add(new_item)
        
        db.session.commit()
        
        flash('预算单复制成功！', 'success')
        return redirect(url_for('package_budget.detail', budget_id=new_budget.id))
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in duplicate budget: {e}")
        flash('复制预算单时发生数据库错误', 'error')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in duplicate budget: {e}")
        flash('复制预算单时发生错误', 'error')
    
    return redirect(url_for('package_budget.detail', budget_id=budget_id))


@package_budget.route('/<int:budget_id>/export', methods=['GET'])
def export_budget(budget_id):
    """导出预算单为JSON格式"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        
        # 构建导出数据
        export_data = {
            'budget': {
                'id': budget.id,
                'package_name': budget.package_name,
                'adult_count': budget.adult_count,
                'child_count': budget.child_count,
                'currency': budget.currency,
                'status': budget.status,
                'is_template': budget.is_template,
                'remarks': budget.remarks,
                'created_at': budget.created_at.isoformat() if budget.created_at else None,
                'updated_at': budget.updated_at.isoformat() if budget.updated_at else None,
                'created_by': budget.created_by,
                'total_price': float(budget.total_price)
            },
            'items': []
        }
        
        for item in budget.items:
            export_data['items'].append({
                'id': item.id,
                'category': item.category,
                'item_name': item.item_name,
                'adult_price': float(item.adult_price) if item.adult_price else None,
                'child_price': float(item.child_price) if item.child_price else None,
                'total_override': float(item.total_override) if item.total_override else None,
                'count_adult_apply': item.count_adult_apply,
                'count_child_apply': item.count_child_apply,
                'adult_count_override': item.adult_count_override,
                'child_count_override': item.child_count_override,
                'sort_order': item.sort_order,
                'tax_rate': float(item.tax_rate) if item.tax_rate else None,
                'tax_amount': float(item.tax_amount) if item.tax_amount else None,
                'is_optional': item.is_optional,
                'remarks': item.remarks,
                'subtotal': float(item.subtotal)
            })
        
        return jsonify(export_data)
    
    except Exception as e:
        current_app.logger.error(f"Error in export budget: {e}")
        return jsonify({'error': '导出失败'}), 500


@package_budget.route('/import', methods=['GET', 'POST'])
@csrf.exempt
def import_budget():
    """导入预算单"""
    if request.method == 'POST':
        try:
            # 这里可以实现从JSON文件导入预算单的功能
            # 暂时返回提示信息
            flash('导入功能正在开发中', 'info')
            return redirect(url_for('package_budget.list_budgets'))
        
        except Exception as e:
            current_app.logger.error(f"Error in import budget: {e}")
            flash('导入预算单时发生错误', 'error')
    
    return render_template('package/budget/import.html')


@package_budget.route('/templates')
def list_templates():
    """模板列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        
        # 查询模板
        query = BudgetHeader.query.filter(BudgetHeader.is_template == True)
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    BudgetHeader.package_name.ilike(f'%{search}%'),
                    BudgetHeader.remarks.ilike(f'%{search}%')
                )
            )
        
        # 排序
        query = query.order_by(BudgetHeader.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        templates = pagination.items
        
        return render_template('package/budget/templates.html', 
                             templates=templates, 
                             pagination=pagination)
    
    except Exception as e:
        current_app.logger.error(f"Error in list templates: {e}")
        flash('获取模板列表时发生错误', 'error')
        return render_template('package/budget/templates.html', templates=[], pagination=None)


@package_budget.route('/<int:budget_id>/download_txt', methods=['GET'])
def download_budget_txt(budget_id):
    """下载预算项目为txt文件（顾客版本）"""
    try:
        budget = BudgetHeader.query.get_or_404(budget_id)
        
        # 检查预算单是否存在项目
        if not budget.items:
            flash('预算单中没有项目，无法生成下载文件', 'warning')
            return redirect(url_for('package_budget.detail', budget_id=budget_id))
        
        # 生成txt内容
        content = []
        
        # 标题部分
        content.append("=" * 60)
        content.append(f"旅游配套详情")
        content.append("=" * 60)
        content.append("")
        
        # 基本信息
        content.append("【配套信息】")
        content.append(f"配套名称：{budget.package_name}")
        content.append(f"成人人数：{budget.adult_count}人")
        content.append(f"儿童人数：{budget.child_count}人")
        content.append("")
        
        # 项目明细
        content.append("【包含项目】")
        content.append("-" * 40)
        content.append("")
        
        total_price = 0
        
        for i, item in enumerate(budget.items, 1):
            # 项目标题
            content.append(f"{i:2d}. {item.item_name}")
            
            # 项目详情
            if item.item_details:
                details_lines = item.item_details.split('\n')
                for line in details_lines:
                    if line.strip():
                        content.append(f"    {line.strip()}")
            
            # 计算项目总价（用于内部计算，不显示给顾客）
            item_total = item.subtotal or 0
            total_price += item_total
            
            # 可选项目标记
            if item.is_optional:
                content.append("    [可选项目]")
            
            # 备注（如果有重要信息）
            if item.remarks:
                content.append(f"    备注：{item.remarks}")
            
            content.append("")
        
        # 总价
        content.append("=" * 60)
        content.append("【总价】")
        content.append("-" * 40)
        content.append(f"总价：{total_price:.2f} {budget.currency}")
        content.append("=" * 60)
        content.append("")
        
        # 备注信息
        if budget.remarks:
            content.append("【备注】")
            content.append("-" * 40)
            content.append(budget.remarks)
            content.append("")
        
        # 生成纯ASCII文件名避免编码问题
        filename = f"{budget.package_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        response = Response('\n'.join(content), mimetype='text/plain; charset=utf-8')
        response.headers['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response
    except Exception as e:
        current_app.logger.error(f"Error in download_budget_txt for budget {budget_id}: {e}")
        flash(f'下载失败: {str(e)}', 'error')
        return redirect(url_for('package_budget.detail', budget_id=budget_id)) 