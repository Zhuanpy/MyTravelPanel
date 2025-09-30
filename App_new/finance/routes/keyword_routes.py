# -*- coding: utf-8 -*-
"""
银行关键词管理路由
提供关键词的增删改查、批量导入、导出等功能
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from App_new.exts import csrf, db
from App_new.utils.decorators import staff_only
from App_new.finance.models.bank_keywords import BankStatementKeyword, BankKeywordCategory
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
keyword_blue = Blueprint('keyword_routes', __name__)


@keyword_blue.route('/keywords')
@login_required
@staff_only
def keyword_list():
    """关键词列表页面"""
    bank_name = request.args.get('bank', '').strip()
    keyword_type = request.args.get('type', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # 构建查询
    query = BankStatementKeyword.query
    if bank_name:
        query = query.filter(BankStatementKeyword.bank_name == bank_name)
    if keyword_type:
        query = query.filter(BankStatementKeyword.keyword_type == keyword_type)
    
    # 分页
    pagination = query.order_by(
        BankStatementKeyword.bank_name.asc(),
        BankStatementKeyword.keyword_type.asc(),
        BankStatementKeyword.keyword.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    keywords = pagination.items
    
    # 获取银行列表和类型列表
    banks = db.session.query(BankStatementKeyword.bank_name).distinct().all()
    types = db.session.query(BankStatementKeyword.keyword_type).distinct().all()
    
    # 银行名称映射
    bank_names = {
        'UOB': '大华银行',
        'OCBC': '华侨银行', 
        'CMB': '招商银行'
    }
    
    return render_template('finance/keywords/keyword_list.html',
                         keywords=keywords,
                         pagination=pagination,
                         banks=[b[0] for b in banks],
                         types=[t[0] for t in types],
                         current_bank=bank_name,
                         current_type=keyword_type)


@keyword_blue.route('/keywords/add', methods=['GET', 'POST'])
@login_required
@staff_only
@csrf.exempt
def keyword_add():
    """添加关键词"""
    # 获取预设银行参数
    preset_bank = request.args.get('bank', '').strip()
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            keyword = BankStatementKeyword(
                bank_name=data.get('bank_name', '').strip(),
                keyword_type=data.get('keyword_type', '').strip(),
                keyword=data.get('keyword', '').strip(),
                description=data.get('description', '').strip(),
                is_active=bool(data.get('is_active', True)) if isinstance(data.get('is_active'), bool) else data.get('is_active', '1') in ['1', 'true', 'True', 'on', 'yes']
            )
            
            db.session.add(keyword)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': '关键词添加成功'})
            flash('关键词添加成功', 'success')
            return redirect(url_for('keyword_routes.keyword_list', bank=preset_bank))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"添加关键词失败: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'message': f'添加失败：{str(e)}'})
            flash(f'添加失败：{str(e)}', 'error')
            return redirect(url_for('keyword_routes.keyword_add', bank=preset_bank))
    
    # 银行名称映射
    bank_names = {
        'UOB': '大华银行',
        'OCBC': '华侨银行', 
        'CMB': '招商银行'
    }
    
    return render_template('finance/keywords/keyword_form.html',
                         form_title="添加关键词",
                         preset_bank=preset_bank,
                         bank_names=bank_names)


@keyword_blue.route('/keywords/edit/<int:keyword_id>', methods=['GET', 'POST'])
@login_required
@staff_only
def keyword_edit(keyword_id):
    """编辑关键词"""
    keyword = BankStatementKeyword.query.get_or_404(keyword_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            keyword.bank_name = data.get('bank_name', '').strip()
            keyword.keyword_type = data.get('keyword_type', '').strip()
            keyword.keyword = data.get('keyword', '').strip()
            keyword.description = data.get('description', '').strip()
            keyword.is_active = bool(data.get('is_active', True)) if isinstance(data.get('is_active'), bool) else data.get('is_active', '1') in ['1', 'true', 'True', 'on', 'yes']
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': '关键词更新成功'})
            flash('关键词更新成功', 'success')
            return redirect(url_for('keyword_routes.keyword_list'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新关键词失败: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})
            flash(f'更新失败：{str(e)}', 'error')
            return redirect(url_for('keyword_routes.keyword_edit', keyword_id=keyword_id))
    
    return render_template('finance/keywords/keyword_form.html', keyword=keyword)


@keyword_blue.route('/keywords/delete/<int:keyword_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def keyword_delete(keyword_id):
    """删除关键词"""
    try:
        keyword = BankStatementKeyword.query.get_or_404(keyword_id)
        db.session.delete(keyword)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': '关键词删除成功'})
        flash('关键词删除成功', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除关键词失败: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('keyword_routes.keyword_list'))


@keyword_blue.route('/keywords/batch_import', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def keyword_batch_import():
    """批量导入关键词"""
    try:
        data = request.get_json()
        keywords_data = data.get('keywords', [])
        bank_name = data.get('bank_name', '').strip()
        
        if not bank_name or not keywords_data:
            return jsonify({'success': False, 'message': '银行名称和关键词数据不能为空'})
        
        imported_count = 0
        for item in keywords_data:
            try:
                keyword = BankStatementKeyword(
                    bank_name=bank_name,
                    keyword_type=item.get('type', 'other').strip(),
                    keyword=item.get('keyword', '').strip(),
                    description=item.get('description', '').strip(),
                    is_active=item.get('is_active', True)
                )
                db.session.add(keyword)
                imported_count += 1
            except Exception as e:
                logger.warning(f"跳过无效关键词数据: {item}, 错误: {str(e)}")
                continue
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'成功导入 {imported_count} 个关键词'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量导入关键词失败: {str(e)}")
        return jsonify({'success': False, 'message': f'导入失败：{str(e)}'})


@keyword_blue.route('/keywords/export/<bank_name>')
@login_required
@staff_only
def keyword_export(bank_name):
    """导出银行关键词"""
    try:
        keywords = BankStatementKeyword.query.filter_by(bank_name=bank_name).all()
        
        # 按类型分组
        grouped = {}
        for kw in keywords:
            if kw.keyword_type not in grouped:
                grouped[kw.keyword_type] = []
            grouped[kw.keyword_type].append(kw.keyword)
        
        # 生成txt格式内容
        content = f"# {bank_name} 银行关键词\n\n"
        for kw_type, kw_list in grouped.items():
            content += f"## {kw_type}\n"
            for kw in sorted(kw_list):
                content += f"{kw}\n"
            content += "\n"
        
        from flask import Response
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename={bank_name}_keywords.txt'}
        )
        
    except Exception as e:
        logger.error(f"导出关键词失败: {str(e)}")
        flash(f'导出失败：{str(e)}', 'error')
        return redirect(url_for('keyword_routes.keyword_list'))


@keyword_blue.route('/keywords/from_txt', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def keyword_from_txt():
    """从txt文件导入关键词（模拟UOB的txt读取方式）"""
    try:
        data = request.get_json()
        bank_name = data.get('bank_name', '').strip()
        txt_content = data.get('txt_content', '').strip()
        keyword_type = data.get('keyword_type', 'other').strip()
        
        if not bank_name or not txt_content:
            return jsonify({'success': False, 'message': '银行名称和txt内容不能为空'})
        
        # 解析txt内容
        keywords = []
        for line in txt_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                keywords.append(line)
        
        # 去重
        keywords = list(set(keywords))
        
        # 批量插入，处理重复关键词
        imported_count = 0
        skipped_count = 0
        skipped_keywords = []
        
        for keyword_text in keywords:
            try:
                # 检查是否已存在相同的关键词
                existing = BankStatementKeyword.query.filter_by(
                    bank_name=bank_name,
                    keyword=keyword_text
                ).first()
                
                if existing:
                    skipped_count += 1
                    skipped_keywords.append(keyword_text)
                    logger.info(f"跳过已存在的关键词: {keyword_text}")
                    continue
                
                keyword = BankStatementKeyword(
                    bank_name=bank_name,
                    keyword_type=keyword_type,
                    keyword=keyword_text,
                    description=f'从txt导入的{keyword_type}关键词',
                    is_active=True
                )
                db.session.add(keyword)
                imported_count += 1
                
            except Exception as e:
                skipped_count += 1
                skipped_keywords.append(keyword_text)
                logger.warning(f"跳过关键词 {keyword_text}: {str(e)}")
                continue
        
        db.session.commit()
        
        # 构建返回消息
        message = f'成功导入 {imported_count} 个关键词'
        if skipped_count > 0:
            message += f'，跳过 {skipped_count} 个重复或无效关键词'
            if len(skipped_keywords) <= 5:
                message += f'：{", ".join(skipped_keywords)}'
            else:
                message += f'：{", ".join(skipped_keywords[:5])} 等'
        
        return jsonify({'success': True, 'message': message, 'imported_count': imported_count, 'skipped_count': skipped_count})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"从txt导入关键词失败: {str(e)}")
        return jsonify({'success': False, 'message': f'导入失败：{str(e)}'})


@keyword_blue.route('/keywords/import_txt', methods=['GET', 'POST'])
@login_required
@staff_only
def import_keywords_txt():
    """从TXT文件导入关键词"""
    # 获取预设银行参数
    preset_bank = request.args.get('bank', '').strip()
    
    if request.method == 'GET':
        # 银行名称映射
        bank_names = {
            'UOB': '大华银行',
            'OCBC': '华侨银行', 
            'CMB': '招商银行'
        }
        return render_template('finance/keywords/import_txt.html',
                             preset_bank=preset_bank,
                             bank_names=bank_names)
    
    try:
        if 'file' not in request.files:
            flash('请选择文件', 'error')
            return redirect(url_for('keyword_routes.import_keywords_txt', bank=preset_bank))
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'error')
            return redirect(url_for('keyword_routes.import_keywords_txt', bank=preset_bank))
        
        if not file.filename.endswith('.txt'):
            flash('只支持TXT文件', 'error')
            return redirect(url_for('keyword_routes.import_keywords_txt', bank=preset_bank))
        
        # 读取文件内容
        content = file.read().decode('utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not lines:
            flash('文件为空或格式错误', 'error')
            return redirect(url_for('keyword_routes.import_keywords_txt', bank=preset_bank))
        
        # 获取表单数据
        bank_name = request.form.get('bank_name', preset_bank or 'UOB')
        keyword_type = request.form.get('keyword_type', 'personal')
        
        # 解析关键词
        imported_count = 0
        for line in lines:
            if line.startswith('#') or line.startswith('##'):
                continue  # 跳过注释行
            
            # 简单解析：每行一个关键词
            keyword_text = line.strip()
            if keyword_text:
                # 检查是否已存在
                existing = BankStatementKeyword.query.filter_by(
                    bank_name=bank_name,
                    keyword=keyword_text
                ).first()
                if not existing:
                    keyword = BankStatementKeyword(
                        bank_name=bank_name,
                        keyword_type=keyword_type,
                        keyword=keyword_text,
                        description=f'从TXT文件导入: {file.filename}',
                        is_active=True
                    )
                    db.session.add(keyword)
                    imported_count += 1
        
        db.session.commit()
        flash(f'成功导入 {imported_count} 个关键词', 'success')
        return redirect(url_for('keyword_routes.keyword_list', bank=bank_name))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"TXT导入关键词失败: {str(e)}")
        flash(f'导入失败：{str(e)}', 'error')
        return redirect(url_for('keyword_routes.import_keywords_txt', bank=preset_bank))


def get_keywords_for_bank(bank_name, keyword_type=None):
    """获取指定银行的关键词列表（供其他模块调用）"""
    query = BankStatementKeyword.query.filter_by(bank_name=bank_name, is_active=True)
    if keyword_type:
        query = query.filter_by(keyword_type=keyword_type)
    
    keywords = [kw.keyword for kw in query.all()]
    return keywords


def extract_keywords_from_text(text, bank_name, keyword_type=None):
    """从文本中提取关键词（供其他模块调用）"""
    if not text:
        return []
    
    keywords = get_keywords_for_bank(bank_name, keyword_type)
    found_keywords = [keyword for keyword in keywords if keyword in text]
    return found_keywords
