# MyTravelPanel 基于角色的分步实现计划

## 🎯 角色定义与权限规划

### 角色层级结构
```
管理员 (Admin)
├── 管理全站数据
├── 用户管理
├── 权限管理  
├── 订单管理
└── 内容发布

公司员工 (Staff)
├── 管理所属项目
├── 新增/修改报价
├── 上传文件
└── 项目进度管理

会员客户 (Member)
├── 查看订单
├── 下单
└── 查看报价/发票

普通访客 (Guest)
└── 浏览公开信息
```

## 📋 分步实现计划

### 第一阶段：基础角色系统 (Week 1-2)

#### Week 1: 角色模型与权限定义

**Day 1-2: 角色数据模型**
- [ ] **Task 1.1.1**: 扩展Role模型
  ```python
  # App/models/auth.py
  class Role(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      name = db.Column(db.String(50), unique=True)  # admin, staff, member, guest
      description = db.Column(db.String(200))
      permissions = db.Column(db.JSON)  # 存储权限列表
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
  ```

- [ ] **Task 1.1.2**: 定义角色权限常量
  ```python
  # App/utils/permissions.py
  ROLE_PERMISSIONS = {
      'admin': [
          'manage_all_data',      # 管理全站数据
          'manage_users',         # 用户管理
          'manage_roles',         # 权限管理
          'manage_orders',        # 订单管理
          'publish_content',      # 内容发布
          'view_analytics',       # 查看统计
          'system_config'         # 系统配置
      ],
      'staff': [
          'manage_own_projects',  # 管理所属项目
          'create_quotes',        # 新增报价
          'edit_quotes',          # 修改报价
          'upload_files',         # 上传文件
          'update_progress',      # 更新项目进度
          'view_own_orders'       # 查看相关订单
      ],
      'member': [
          'view_own_orders',      # 查看自己的订单
          'place_orders',         # 下单
          'view_quotes',          # 查看报价
          'view_invoices',        # 查看发票
          'edit_profile'          # 编辑个人资料
      ],
      'guest': [
          'view_public_info',     # 浏览公开信息
          'view_visa_services',   # 查看签证服务
          'view_tour_packages'    # 查看旅游配套
      ]
  }
  ```

**Day 3-4: 权限检查系统**
- [ ] **Task 1.2.1**: 创建权限检查装饰器
  ```python
  # App/utils/decorators.py
  def require_role(role_name):
      def decorator(f):
          @wraps(f)
          def decorated_function(*args, **kwargs):
              if not current_user.is_authenticated:
                  return redirect(url_for('auth.login'))
              if current_user.role.name != role_name and current_user.role.name != 'admin':
                  abort(403)
              return f(*args, **kwargs)
          return decorated_function
      return decorator

  def require_permission(permission):
      def decorator(f):
          @wraps(f)
          def decorated_function(*args, **kwargs):
              if not current_user.is_authenticated:
                  return redirect(url_for('auth.login'))
              if not has_permission(current_user, permission):
                  abort(403)
              return f(*args, **kwargs)
          return decorated_function
      return decorator
  ```

**Day 5-7: 基础角色页面**
- [ ] **Task 1.3.1**: 创建角色管理页面
  - 文件: `App/templates/admin/roles.html`
  - 功能: 角色列表、创建角色、编辑权限

- [ ] **Task 1.3.2**: 创建用户角色分配页面
  - 文件: `App/templates/admin/user_roles.html`
  - 功能: 为用户分配角色

#### Week 2: 访客功能实现

**Day 1-3: 公开页面**
- [ ] **Task 1.4.1**: 签证服务展示页面
  ```python
  # App/routes/public.py
  @app.route('/visa-services')
  def visa_services():
      visa_types = VisaTypes.query.filter_by(is_active=True).all()
      return render_template('public/visa_services.html', visa_types=visa_types)
  ```
  文件: `App/templates/public/visa_services.html`

- [ ] **Task 1.4.2**: 旅游配套展示页面
  ```python
  @app.route('/tour-packages')
  def tour_packages():
      packages = TourPackage.query.filter_by(is_active=True).all()
      return render_template('public/tour_packages.html', packages=packages)
  ```
  文件: `App/templates/public/tour_packages.html`

- [ ] **Task 1.4.3**: 首页优化
  - 文件: `App/templates/index.html`
  - 功能: 服务介绍、快速导航

**Day 4-5: 访客导航**
- [ ] **Task 1.5.1**: 更新导航菜单
  ```html
  <!-- App/templates/base.html -->
  <nav class="navbar">
      <div class="nav-brand">MyTravelPanel</div>
      <div class="nav-menu">
          {% if current_user.is_authenticated %}
              {% if current_user.role.name == 'admin' %}
                  <!-- 管理员菜单 -->
              {% elif current_user.role.name == 'staff' %}
                  <!-- 员工菜单 -->
              {% elif current_user.role.name == 'member' %}
                  <!-- 会员菜单 -->
              {% endif %}
          {% else %}
              <!-- 访客菜单 -->
              <a href="{{ url_for('public.visa_services') }}">签证服务</a>
              <a href="{{ url_for('public.tour_packages') }}">旅游配套</a>
              <a href="{{ url_for('auth.login') }}">登录</a>
              <a href="{{ url_for('auth.register') }}">注册</a>
          {% endif %}
      </div>
  </nav>
  ```

**Day 6-7: 访客功能测试**
- [ ] **Task 1.6.1**: 访客功能测试
  - 文件: `scripts/test_guest_features.py`
  - 测试: 公开页面访问、导航菜单

### 第二阶段：会员客户功能 (Week 3-4)

#### Week 3: 会员注册与基础功能

**Day 1-3: 会员注册系统**
- [ ] **Task 2.1.1**: 会员注册表单
  ```python
  # App/forms/auth_forms.py
  class MemberRegistrationForm(FlaskForm):
      username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=20)])
      email = StringField('邮箱', validators=[DataRequired(), Email()])
      password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
      confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
      phone = StringField('手机号', validators=[DataRequired()])
      company = StringField('公司名称')
      submit = SubmitField('注册')
  ```

- [ ] **Task 2.1.2**: 会员注册路由
  ```python
  # App/routes/auth.py
  @app.route('/register/member', methods=['GET', 'POST'])
  def register_member():
      form = MemberRegistrationForm()
      if form.validate_on_submit():
          # 创建用户并分配member角色
          user = User(
              username=form.username.data,
              email=form.email.data,
              role_id=get_role_id('member')
          )
          user.set_password(form.password.data)
          db.session.add(user)
          db.session.commit()
          flash('注册成功！请登录。', 'success')
          return redirect(url_for('auth.login'))
      return render_template('auth/register_member.html', form=form)
  ```

**Day 4-5: 会员仪表板**
- [ ] **Task 2.2.1**: 会员仪表板
  ```python
  # App/routes/member.py
  @app.route('/member/dashboard')
  @login_required
  @require_role('member')
  def member_dashboard():
      user_orders = Order.query.filter_by(user_id=current_user.id).all()
      recent_quotes = Quote.query.filter_by(user_id=current_user.id).order_by(Quote.created_at.desc()).limit(5).all()
      return render_template('member/dashboard.html', orders=user_orders, quotes=recent_quotes)
  ```
  文件: `App/templates/member/dashboard.html`

**Day 6-7: 订单查看功能**
- [ ] **Task 2.3.1**: 会员订单列表
  ```python
  @app.route('/member/orders')
  @login_required
  @require_role('member')
  def member_orders():
      page = request.args.get('page', 1, type=int)
      orders = Order.query.filter_by(user_id=current_user.id).paginate(
          page=page, per_page=10, error_out=False)
      return render_template('member/orders.html', orders=orders)
  ```
  文件: `App/templates/member/orders.html`

#### Week 4: 会员下单与查看功能

**Day 1-3: 下单功能**
- [ ] **Task 2.4.1**: 下单页面
  ```python
  @app.route('/member/place_order/<int:package_id>', methods=['GET', 'POST'])
  @login_required
  @require_role('member')
  def place_order(package_id):
      package = TourPackage.query.get_or_404(package_id)
      form = OrderForm()
      if form.validate_on_submit():
          order = Order(
              user_id=current_user.id,
              package_id=package_id,
              quantity=form.quantity.data,
              total_amount=package.price * form.quantity.data,
              status='pending'
          )
          db.session.add(order)
          db.session.commit()
          flash('订单提交成功！', 'success')
          return redirect(url_for('member.member_orders'))
      return render_template('member/place_order.html', package=package, form=form)
  ```
  文件: `App/templates/member/place_order.html`

**Day 4-5: 报价与发票查看**
- [ ] **Task 2.5.1**: 报价查看页面
  ```python
  @app.route('/member/quotes')
  @login_required
  @require_role('member')
  def member_quotes():
      quotes = Quote.query.filter_by(user_id=current_user.id).all()
      return render_template('member/quotes.html', quotes=quotes)
  ```
  文件: `App/templates/member/quotes.html`

- [ ] **Task 2.5.2**: 发票查看页面
  ```python
  @app.route('/member/invoices')
  @login_required
  @require_role('member')
  def member_invoices():
      invoices = Invoice.query.filter_by(user_id=current_user.id).all()
      return render_template('member/invoices.html', invoices=invoices)
  ```
  文件: `App/templates/member/invoices.html`

**Day 6-7: 会员功能测试**
- [ ] **Task 2.6.1**: 会员功能测试
  - 文件: `scripts/test_member_features.py`
  - 测试: 注册、登录、下单、查看订单

### 第三阶段：公司员工功能 (Week 5-7)

#### Week 5: 员工项目管理

**Day 1-3: 员工仪表板**
- [ ] **Task 3.1.1**: 员工仪表板
  ```python
  # App/routes/staff.py
  @app.route('/staff/dashboard')
  @login_required
  @require_role('staff')
  def staff_dashboard():
      # 获取员工负责的项目
      assigned_projects = Project.query.filter_by(staff_id=current_user.id).all()
      pending_quotes = Quote.query.filter_by(status='pending').all()
      return render_template('staff/dashboard.html', 
                           projects=assigned_projects, 
                           quotes=pending_quotes)
  ```
  文件: `App/templates/staff/dashboard.html`

**Day 4-5: 项目列表管理**
- [ ] **Task 3.2.1**: 员工项目列表
  ```python
  @app.route('/staff/projects')
  @login_required
  @require_role('staff')
  def staff_projects():
      projects = Project.query.filter_by(staff_id=current_user.id).all()
      return render_template('staff/projects.html', projects=projects)
  ```
  文件: `App/templates/staff/projects.html`

**Day 6-7: 项目详情页面**
- [ ] **Task 3.3.1**: 项目详情与编辑
  ```python
  @app.route('/staff/project/<int:project_id>')
  @login_required
  @require_role('staff')
  def staff_project_detail(project_id):
      project = Project.query.get_or_404(project_id)
      # 检查权限：只能查看自己负责的项目
      if project.staff_id != current_user.id:
          abort(403)
      return render_template('staff/project_detail.html', project=project)
  ```
  文件: `App/templates/staff/project_detail.html`

#### Week 6: 报价管理功能

**Day 1-3: 报价创建与编辑**
- [ ] **Task 3.4.1**: 报价创建页面
  ```python
  @app.route('/staff/quote/create', methods=['GET', 'POST'])
  @login_required
  @require_role('staff')
  def create_quote():
      form = QuoteForm()
      if form.validate_on_submit():
          quote = Quote(
              project_id=form.project_id.data,
              user_id=form.user_id.data,
              amount=form.amount.data,
              description=form.description.data,
              created_by=current_user.id
          )
          db.session.add(quote)
          db.session.commit()
          flash('报价创建成功！', 'success')
          return redirect(url_for('staff.staff_projects'))
      return render_template('staff/create_quote.html', form=form)
  ```
  文件: `App/templates/staff/create_quote.html`

**Day 4-5: 报价列表管理**
- [ ] **Task 3.5.1**: 报价列表页面
  ```python
  @app.route('/staff/quotes')
  @login_required
  @require_role('staff')
  def staff_quotes():
      # 获取员工创建的报价
      quotes = Quote.query.filter_by(created_by=current_user.id).all()
      return render_template('staff/quotes.html', quotes=quotes)
  ```
  文件: `App/templates/staff/quotes.html`

**Day 6-7: 报价编辑功能**
- [ ] **Task 3.6.1**: 报价编辑页面
  ```python
  @app.route('/staff/quote/<int:quote_id>/edit', methods=['GET', 'POST'])
  @login_required
  @require_role('staff')
  def edit_quote(quote_id):
      quote = Quote.query.get_or_404(quote_id)
      # 检查权限：只能编辑自己创建的报价
      if quote.created_by != current_user.id:
          abort(403)
      form = QuoteForm(obj=quote)
      if form.validate_on_submit():
          form.populate_obj(quote)
          db.session.commit()
          flash('报价更新成功！', 'success')
          return redirect(url_for('staff.staff_quotes'))
      return render_template('staff/edit_quote.html', form=form, quote=quote)
  ```
  文件: `App/templates/staff/edit_quote.html`

#### Week 7: 文件上传与进度管理

**Day 1-3: 文件上传功能**
- [ ] **Task 3.7.1**: 文件上传页面
  ```python
  @app.route('/staff/project/<int:project_id>/upload', methods=['GET', 'POST'])
  @login_required
  @require_role('staff')
  def upload_project_files(project_id):
      project = Project.query.get_or_404(project_id)
      if project.staff_id != current_user.id:
          abort(403)
      
      if request.method == 'POST':
          files = request.files.getlist('files')
          for file in files:
              if file and allowed_file(file.filename):
                  filename = secure_filename(file.filename)
                  file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                  file.save(file_path)
                  
                  # 保存文件记录
                  project_file = ProjectFile(
                      project_id=project_id,
                      filename=filename,
                      file_path=file_path,
                      uploaded_by=current_user.id
                  )
                  db.session.add(project_file)
          db.session.commit()
          flash('文件上传成功！', 'success')
          return redirect(url_for('staff.staff_project_detail', project_id=project_id))
      
      return render_template('staff/upload_files.html', project=project)
  ```
  文件: `App/templates/staff/upload_files.html`

**Day 4-5: 项目进度更新**
- [ ] **Task 3.8.1**: 进度更新页面
  ```python
  @app.route('/staff/project/<int:project_id>/progress', methods=['GET', 'POST'])
  @login_required
  @require_role('staff')
  def update_project_progress(project_id):
      project = Project.query.get_or_404(project_id)
      if project.staff_id != current_user.id:
          abort(403)
      
      form = ProgressUpdateForm()
      if form.validate_on_submit():
          progress = ProjectProgress(
              project_id=project_id,
              status=form.status.data,
              description=form.description.data,
              updated_by=current_user.id
          )
          db.session.add(progress)
          project.status = form.status.data
          db.session.commit()
          flash('进度更新成功！', 'success')
          return redirect(url_for('staff.staff_project_detail', project_id=project_id))
      
      return render_template('staff/update_progress.html', project=project, form=form)
  ```
  文件: `App/templates/staff/update_progress.html`

**Day 6-7: 员工功能测试**
- [ ] **Task 3.9.1**: 员工功能测试
  - 文件: `scripts/test_staff_features.py`
  - 测试: 项目管理、报价创建、文件上传、进度更新

### 第四阶段：管理员功能 (Week 8-10)

#### Week 8: 管理员仪表板与用户管理

**Day 1-3: 管理员仪表板**
- [ ] **Task 4.1.1**: 管理员主仪表板
  ```python
  # App/routes/admin.py
  @app.route('/admin/dashboard')
  @login_required
  @require_role('admin')
  def admin_dashboard():
      # 统计数据
      stats = {
          'total_users': User.query.count(),
          'total_orders': Order.query.count(),
          'total_projects': Project.query.count(),
          'total_revenue': db.session.query(func.sum(Order.total_amount)).scalar() or 0,
          'pending_quotes': Quote.query.filter_by(status='pending').count(),
          'active_projects': Project.query.filter_by(status='active').count()
      }
      
      # 最近活动
      recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
      recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
      
      return render_template('admin/dashboard.html', 
                           stats=stats, 
                           recent_orders=recent_orders,
                           recent_users=recent_users)
  ```
  文件: `App/templates/admin/dashboard.html`

**Day 4-5: 用户管理**
- [ ] **Task 4.2.1**: 用户列表管理
  ```python
  @app.route('/admin/users')
  @login_required
  @require_role('admin')
  def admin_users():
      page = request.args.get('page', 1, type=int)
      users = User.query.paginate(page=page, per_page=20, error_out=False)
      return render_template('admin/users.html', users=users)
  ```
  文件: `App/templates/admin/users.html`

- [ ] **Task 4.2.2**: 用户详情与编辑
  ```python
  @app.route('/admin/user/<int:user_id>')
  @login_required
  @require_role('admin')
  def admin_user_detail(user_id):
      user = User.query.get_or_404(user_id)
      return render_template('admin/user_detail.html', user=user)
  ```
  文件: `App/templates/admin/user_detail.html`

**Day 6-7: 角色权限管理**
- [ ] **Task 4.3.1**: 角色管理页面
  ```python
  @app.route('/admin/roles')
  @login_required
  @require_role('admin')
  def admin_roles():
      roles = Role.query.all()
      return render_template('admin/roles.html', roles=roles)
  ```
  文件: `App/templates/admin/roles.html`

#### Week 9: 订单与内容管理

**Day 1-3: 订单管理**
- [ ] **Task 4.4.1**: 订单列表管理
  ```python
  @app.route('/admin/orders')
  @login_required
  @require_role('admin')
  def admin_orders():
      page = request.args.get('page', 1, type=int)
      status_filter = request.args.get('status', '')
      
      query = Order.query
      if status_filter:
          query = query.filter_by(status=status_filter)
      
      orders = query.order_by(Order.created_at.desc()).paginate(
          page=page, per_page=20, error_out=False)
      return render_template('admin/orders.html', orders=orders, status_filter=status_filter)
  ```
  文件: `App/templates/admin/orders.html`

- [ ] **Task 4.4.2**: 订单详情与处理
  ```python
  @app.route('/admin/order/<int:order_id>')
  @login_required
  @require_role('admin')
  def admin_order_detail(order_id):
      order = Order.query.get_or_404(order_id)
      return render_template('admin/order_detail.html', order=order)
  ```
  文件: `App/templates/admin/order_detail.html`

**Day 4-5: 内容发布管理**
- [ ] **Task 4.5.1**: 签证服务管理
  ```python
  @app.route('/admin/visa-services')
  @login_required
  @require_role('admin')
  def admin_visa_services():
      visa_types = VisaTypes.query.all()
      return render_template('admin/visa_services.html', visa_types=visa_types)
  ```
  文件: `App/templates/admin/visa_services.html`

- [ ] **Task 4.5.2**: 旅游配套管理
  ```python
  @app.route('/admin/tour-packages')
  @login_required
  @require_role('admin')
  def admin_tour_packages():
      packages = TourPackage.query.all()
      return render_template('admin/tour_packages.html', packages=packages)
  ```
  文件: `App/templates/admin/tour_packages.html`

**Day 6-7: 内容编辑功能**
- [ ] **Task 4.6.1**: 内容编辑页面
  ```python
  @app.route('/admin/content/edit/<content_type>/<int:content_id>', methods=['GET', 'POST'])
  @login_required
  @require_role('admin')
  def admin_edit_content(content_type, content_id):
      if content_type == 'visa':
          content = VisaTypes.query.get_or_404(content_id)
          form = VisaTypeForm(obj=content)
      elif content_type == 'tour':
          content = TourPackage.query.get_or_404(content_id)
          form = TourPackageForm(obj=content)
      
      if form.validate_on_submit():
          form.populate_obj(content)
          db.session.commit()
          flash('内容更新成功！', 'success')
          return redirect(url_for(f'admin.admin_{content_type}s'))
      
      return render_template(f'admin/edit_{content_type}.html', form=form, content=content)
  ```

#### Week 10: 系统配置与统计

**Day 1-3: 系统配置**
- [ ] **Task 4.7.1**: 系统设置页面
  ```python
  @app.route('/admin/settings')
  @login_required
  @require_role('admin')
  def admin_settings():
      form = SystemSettingsForm()
      if form.validate_on_submit():
          # 更新系统配置
          update_system_settings(form.data)
          flash('系统设置更新成功！', 'success')
          return redirect(url_for('admin.admin_settings'))
      return render_template('admin/settings.html', form=form)
  ```
  文件: `App/templates/admin/settings.html`

**Day 4-5: 数据统计与分析**
- [ ] **Task 4.8.1**: 统计报表页面
  ```python
  @app.route('/admin/analytics')
  @login_required
  @require_role('admin')
  def admin_analytics():
      # 收入统计
      monthly_revenue = db.session.query(
          func.date_trunc('month', Order.created_at).label('month'),
          func.sum(Order.total_amount).label('revenue')
      ).group_by('month').order_by('month').all()
      
      # 用户增长统计
      user_growth = db.session.query(
          func.date_trunc('month', User.created_at).label('month'),
          func.count(User.id).label('new_users')
      ).group_by('month').order_by('month').all()
      
      return render_template('admin/analytics.html', 
                           monthly_revenue=monthly_revenue,
                           user_growth=user_growth)
  ```
  文件: `App/templates/admin/analytics.html`

**Day 6-7: 管理员功能测试**
- [ ] **Task 4.9.1**: 管理员功能测试
  - 文件: `scripts/test_admin_features.py`
  - 测试: 用户管理、订单管理、内容发布、统计分析

### 第五阶段：系统集成与优化 (Week 11-12)

#### Week 11: 系统集成

**Day 1-7: 功能集成与测试**
- [ ] **Task 5.1.1**: 角色权限集成测试
- [ ] **Task 5.1.2**: 跨角色功能测试
- [ ] **Task 5.1.3**: 权限边界测试
- [ ] **Task 5.1.4**: 用户体验优化

#### Week 12: 性能优化与安全加固

**Day 1-7: 最终优化**
- [ ] **Task 5.2.1**: 性能优化
- [ ] **Task 5.2.2**: 安全加固
- [ ] **Task 5.2.3**: 文档完善
- [ ] **Task 5.2.4**: 部署准备

## 📊 实施优先级

### 🔥 高优先级 (立即开始)
1. **基础角色系统** (Week 1-2)
2. **访客功能** (Week 2)
3. **会员注册登录** (Week 3)

### ⚡ 中优先级 (第二个月)
1. **会员下单功能** (Week 4)
2. **员工项目管理** (Week 5-6)
3. **报价管理** (Week 6)

### 📈 低优先级 (第三个月)
1. **管理员仪表板** (Week 8)
2. **高级管理功能** (Week 9-10)
3. **系统优化** (Week 11-12)

## 🎯 成功标准

### 功能完整性
- [ ] 四种角色权限清晰分离
- [ ] 各角色功能完整可用
- [ ] 权限检查准确无误

### 用户体验
- [ ] 界面友好，操作简单
- [ ] 响应速度快
- [ ] 错误处理完善

### 安全性
- [ ] 权限验证严格
- [ ] 数据访问控制
- [ ] 防止越权操作

### 可维护性
- [ ] 代码结构清晰
- [ ] 文档完整
- [ ] 易于扩展

## 📋 每周检查清单

### Week 1-2: 基础角色系统
- [ ] 角色模型创建完成
- [ ] 权限定义清晰
- [ ] 访客功能可用
- [ ] 基础测试通过

### Week 3-4: 会员功能
- [ ] 会员注册正常
- [ ] 下单功能完整
- [ ] 订单查看正常
- [ ] 会员测试通过

### Week 5-7: 员工功能
- [ ] 项目管理可用
- [ ] 报价功能完整
- [ ] 文件上传正常
- [ ] 员工测试通过

### Week 8-10: 管理员功能
- [ ] 仪表板可用
- [ ] 用户管理完整
- [ ] 内容发布正常
- [ ] 管理员测试通过

### Week 11-12: 系统集成
- [ ] 功能集成完成
- [ ] 性能优化完成
- [ ] 安全加固完成
- [ ] 全面测试通过

---

**实施建议**: 建议按照优先级逐步实施，每个阶段完成后进行充分测试，确保功能稳定后再进入下一阶段。重点关注权限边界和用户体验。 