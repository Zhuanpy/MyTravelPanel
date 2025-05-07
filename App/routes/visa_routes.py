@visa_routes.route('/visa/project_detail/<int:project_id>')
def visa_project_detail(project_id):
    """显示签证项目详情页面"""
    # 获取当前的visa_status和sort_by参数，用于返回按钮
    current_visa_status = request.args.get('visa_status', 'all')
    current_sort_by = request.args.get('sort_by', 'created_date')

    # 从数据库获取项目信息
    project = Visa_project.query.get_or_404(project_id)
    
    # 获取相关链接（如果有的话）
    related_links = []  # 实际项目中可从数据库获取
    visa_links = []     # 实际项目中可从数据库获取
    
    return render_template(
        'visas/visa_project_detail.html',
        project=project,
        current_visa_status=current_visa_status,
        current_sort_by=current_sort_by,
        related_links=related_links,
        visa_links=visa_links
    )

@visa_routes.route('/visa/update_project_detail/<int:project_id>', methods=['POST'])
def update_project_detail(project_id):
    """更新签证项目的状态或预估日期"""
    project = Visa_project.query.get_or_404(project_id)
    
    # 获取当前的visa_status和sort_by参数，用于重定向回详情页
    current_visa_status = request.form.get('current_visa_status', 'all')
    current_sort_by = request.form.get('current_sort_by', 'created_date')
    
    # 更新签证状态（如果有提交）
    if 'visa_status' in request.form:
        project.visa_status = request.form['visa_status']
    
    # 更新预估日期（如果有提交）
    if 'estimated_date' in request.form and request.form['estimated_date']:
        project.estimated_date = request.form['estimated_date']
    
    db.session.commit()
    
    # 重定向回详情页
    return redirect(url_for('visa_routes.visa_project_detail', 
                           project_id=project_id,
                           visa_status=current_visa_status,
                           sort_by=current_sort_by)) 