# 优化后的 visa_detail 路由
# 将这个函数替换到 visa_project.py 中的对应位置

import time
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from flask import current_app

@visa_project.route('/visa_detail/<project_name>')
@visa_project.route('/visa_detail/id/<int:project_id>')
def visa_detail_optimized(project_name=None, project_id=None):
    """优化后的签证详情页面路由
    
    主要优化点:
    1. 使用 joinedload 减少数据库查询次数
    2. 合并多个条件查询
    3. 批量处理文档信息
    4. 添加性能监控
    """
    start_time = time.time()
    
    def log_timing(step_name):
        """记录每个步骤的耗时"""
        elapsed = time.time() - start_time
        current_app.logger.info(f"[{elapsed:.3f}s] {step_name}")
        print(f"[{elapsed:.3f}s] {step_name}")
    
    try:
        log_timing(f"开始处理请求: project_id={project_id}, project_name={project_name}")
        
        # ========== 步骤 1: 获取项目信息（优化：预加载关联数据）==========
        if project_id:
            # 使用 joinedload 预加载关联的签证类型，避免额外查询
            project = VisaProject.query\
                .options(joinedload('visa_type_relationship'))\
                .get_or_404(project_id)
            log_timing("查询项目完成（使用预加载）")
        else:
            project = VisaProject.query\
                .options(joinedload('visa_type_relationship'))\
                .filter_by(project_folder_name=project_name)\
                .first_or_404()
            log_timing("按名称查询项目完成")
        
        if not project:
            flash('项目不存在或已被删除', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        # 检查项目是否有签证类型
        if not project.visa_type:
            flash('项目缺少签证类型信息', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        # ========== 步骤 2: 获取签证类型信息 ==========
        types_info = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
        if not types_info:
            flash(f'签证类型 "{project.visa_type}" 不存在', 'error')
            return redirect(url_for('visa_project.show_current_all_projects'))
        
        log_timing("查询签证类型完成")
        
        # ========== 步骤 3: 获取链接（优化：合并两个查询为一个）==========
        # 原来: 先查 visa_type_id，没结果再查 visa_countries_id
        # 现在: 用 OR 一次查完
        links = VisaLinks.query.filter(
            or_(
                VisaLinks.visa_type_id == types_info.id,
                VisaLinks.visa_countries_id == types_info.country_id
            )
        ).order_by(VisaLinks.name.asc()).all()
        
        log_timing(f"查询链接完成（找到 {len(links)} 个）")
        
        # ========== 步骤 4: 获取文档数据（优化：预加载关联）==========
        # 使用 joinedload 预加载 singapore_identity，避免 N+1 查询
        documents = VisaDocuments.query\
            .options(joinedload(VisaDocuments.singapore_identity))\
            .join(VisaTypes)\
            .filter(VisaTypes.visa_type == project.visa_type)\
            .all()
        
        log_timing(f"查询文档完成（找到 {len(documents)} 个）")
        
        # ========== 步骤 5: 处理文档数据（优化：批量处理）==========
        document_data = {}
        
        # 获取SHARE身份记录（如果需要的话缓存这个查询）
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        share_identity_id = share_identity.id if share_identity else None
        
        # 批量收集需要查询的文档ID
        document_queries = []
        identity_map = {}  # 保存身份映射，避免重复访问
        
        for doc in documents:
            if doc.singapore_identity_id is None or doc.singapore_identity is None:
                continue
            
            identity_zh = doc.singapore_identity.identity_zh
            if identity_zh not in identity_map:
                identity_map[identity_zh] = doc.singapore_identity_id
                document_queries.append((types_info.id, doc.singapore_identity_id, identity_zh))
        
        # 批量获取文档信息
        for visa_type_id, identity_id, identity_zh in document_queries:
            doc_info = VisaDocuments.get_document_info(visa_type_id, identity_id)
            document_data[identity_zh] = {
                'document_info': doc_info['document_info'],
                'additional_info': doc_info['additional_info']
            }
        
        # 处理SHARE共用资料
        if share_identity_id:
            share_doc_info = VisaDocuments.get_document_info(types_info.id, share_identity_id)
            document_data['SHARE'] = {
                'document_info': share_doc_info['document_info'],
                'additional_info': share_doc_info['additional_info']
            }
        
        log_timing("处理文档数据完成")
        
        # ========== 步骤 6: 获取项目文档状态 ==========
        from App_new.business.visa.models.Visamodels import VisaProjectDocumentStatus
        project_document_statuses = VisaProjectDocumentStatus.query\
            .filter_by(project_id=project.id)\
            .all()
        
        # 将资料状态转换为字典格式
        document_statuses = {}
        for status in project_document_statuses:
            document_statuses[status.document_name] = {
                'id': status.id,
                'is_ready': status.is_ready,
                'notes': status.notes,
                'document_type': status.document_type
            }
        
        log_timing("查询项目文档状态完成")
        
        # 检查项目是否已关联HID和REF
        has_header = project.header_id is not None
        has_ref = project.ref_id is not None
        
        # 记录总耗时
        total_time = time.time() - start_time
        current_app.logger.info(f"页面数据准备完成，总耗时: {total_time:.3f}秒")
        print(f"✅ 页面数据准备完成，总耗时: {total_time:.3f}秒")
        
        return render_template('business/visa/签证项目管理/visa_project_detail.html',
                             project=project,
                             types_info=types_info,
                             links=links,
                             document_data=document_data,
                             document_statuses=document_statuses,
                             has_header=has_header,
                             has_ref=has_ref,
                             page_load_time=f"{total_time:.3f}")  # 传递加载时间到模板
                             
    except Exception as e:
        current_app.logger.error(f"visa_detail 异常: {str(e)}")
        current_app.logger.error(f"详细错误: {traceback.format_exc()}")
        flash(f'获取签证详情时出错: {str(e)}', 'error')
        return redirect(url_for('visa_project.show_current_all_projects'))


# ========== 额外优化建议 ==========

"""
1. 为 VisaDocuments.get_document_info 方法添加缓存:

from flask_caching import Cache
cache = Cache()

@staticmethod
@cache.memoize(timeout=300)  # 缓存5分钟
def get_document_info(visa_type_id, identity_id):
    # 原有逻辑
    pass

2. 添加数据库索引（在迁移脚本中执行）:

CREATE INDEX idx_visa_links_type_and_country 
ON visa_links(visa_type_id, visa_countries_id);

CREATE INDEX idx_visa_documents_type_identity 
ON visa_documents(visa_type_id, singapore_identity_id);

CREATE INDEX idx_visa_project_doc_status_project 
ON visa_project_document_status(project_id);

3. 使用 Redis 缓存整个页面结果:

@cache.cached(timeout=300, key_prefix=lambda: f'visa_detail:{project_id}')
def visa_detail_optimized(project_name=None, project_id=None):
    # ... 代码

4. 异步加载非关键内容:
   - 将文档列表改为AJAX异步加载
   - 首次只加载基本信息，提升首屏速度
"""

