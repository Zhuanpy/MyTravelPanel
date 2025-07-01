# 旅游项目管理系统 - 组件实现示例

## 1. Project Components 实现示例

### 1.1 ProjectList 组件实现

#### HTML 模板结构
```html
<!-- ProjectList 组件模板 -->
<div class="project-list-container" id="projectList">
    <!-- 筛选栏 -->
    <div class="filter-bar">
        <div class="filter-item">
            <label for="statusFilter">项目状态：</label>
            <select id="statusFilter" class="form-select">
                <option value="all">全部状态</option>
                <option value="处理中">处理中</option>
                <option value="待出行">待出行</option>
                <option value="已完成">已完成</option>
                <option value="忽略单">忽略单</option>
            </select>
        </div>
        <div class="filter-item">
            <label for="sortBy">排序方式：</label>
            <select id="sortBy" class="form-select">
                <option value="name">按项目名称</option>
                <option value="created_date">按创建时间</option>
            </select>
        </div>
        <div class="filter-item">
            <label for="searchBox">搜索：</label>
            <input type="text" id="searchBox" class="form-control" placeholder="搜索项目...">
        </div>
    </div>

    <!-- 项目表格 -->
    <div class="project-table-container">
        <table class="project-table">
            <thead>
                <tr>
                    <th>项目ID</th>
                    <th>创建时间</th>
                    <th>项目HID</th>
                    <th>项目名称</th>
                    <th>项目状态</th>
                    <th>联系人</th>
                    <th>联系方式</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="projectTableBody">
                <!-- 动态生成项目行 -->
            </tbody>
        </table>
    </div>

    <!-- 分页组件 -->
    <div class="pagination-container">
        <nav aria-label="项目分页">
            <ul class="pagination" id="pagination">
                <!-- 动态生成分页 -->
            </ul>
        </nav>
    </div>
</div>
```

#### JavaScript 组件类
```javascript
class ProjectList {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            pageSize: 10,
            currentPage: 1,
            ...options
        };
        this.state = {
            projects: [],
            filteredProjects: [],
            filters: {
                status: 'all',
                sortBy: 'name',
                search: ''
            }
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadProjects();
    }

    bindEvents() {
        // 筛选事件
        this.container.querySelector('#statusFilter').addEventListener('change', (e) => {
            this.state.filters.status = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#sortBy').addEventListener('change', (e) => {
            this.state.filters.sortBy = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#searchBox').addEventListener('input', (e) => {
            this.state.filters.search = e.target.value;
            this.applyFilters();
        });
    }

    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            this.state.projects = data.projects;
            this.applyFilters();
        } catch (error) {
            console.error('加载项目失败:', error);
            this.showError('加载项目失败，请稍后重试');
        }
    }

    applyFilters() {
        let filtered = [...this.state.projects];

        // 状态筛选
        if (this.state.filters.status !== 'all') {
            filtered = filtered.filter(project => 
                project.project_status === this.state.filters.status
            );
        }

        // 搜索筛选
        if (this.state.filters.search) {
            const searchTerm = this.state.filters.search.toLowerCase();
            filtered = filtered.filter(project =>
                project.project_name.toLowerCase().includes(searchTerm) ||
                project.contact_person.toLowerCase().includes(searchTerm)
            );
        }

        // 排序
        filtered.sort((a, b) => {
            if (this.state.filters.sortBy === 'name') {
                return a.project_name.localeCompare(b.project_name);
            } else if (this.state.filters.sortBy === 'created_date') {
                return new Date(b.created_at) - new Date(a.created_at);
            }
            return 0;
        });

        this.state.filteredProjects = filtered;
        this.render();
    }

    render() {
        this.renderTable();
        this.renderPagination();
    }

    renderTable() {
        const tbody = this.container.querySelector('#projectTableBody');
        const startIndex = (this.options.currentPage - 1) * this.options.pageSize;
        const endIndex = startIndex + this.options.pageSize;
        const pageProjects = this.state.filteredProjects.slice(startIndex, endIndex);

        tbody.innerHTML = pageProjects.map(project => `
            <tr data-project-id="${project.id}">
                <td>${project.id}</td>
                <td>${new Date(project.created_at).toLocaleDateString()}</td>
                <td>${project.project_hid || 'N/A'}</td>
                <td>${project.project_name}</td>
                <td>
                    <span class="status-badge status-${project.project_status}">
                        ${project.project_status}
                    </span>
                </td>
                <td>${project.contact_person}</td>
                <td>${project.contact_info}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary edit-project" 
                                data-project-id="${project.id}">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-info view-project" 
                                data-project-id="${project.id}">
                            查看
                        </button>
                        <button class="btn btn-sm btn-danger delete-project" 
                                data-project-id="${project.id}">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // 绑定行事件
        this.bindRowEvents();
    }

    bindRowEvents() {
        // 编辑项目
        this.container.querySelectorAll('.edit-project').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projectId = e.target.dataset.projectId;
                this.editProject(projectId);
            });
        });

        // 查看项目
        this.container.querySelectorAll('.view-project').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projectId = e.target.dataset.projectId;
                this.viewProject(projectId);
            });
        });

        // 删除项目
        this.container.querySelectorAll('.delete-project').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projectId = e.target.dataset.projectId;
                this.deleteProject(projectId);
            });
        });
    }

    renderPagination() {
        const totalPages = Math.ceil(this.state.filteredProjects.length / this.options.pageSize);
        const pagination = this.container.querySelector('#pagination');

        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let paginationHTML = '';
        
        // 上一页
        paginationHTML += `
            <li class="page-item ${this.options.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.options.currentPage - 1}">上一页</a>
            </li>
        `;

        // 页码
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || 
                (i >= this.options.currentPage - 2 && i <= this.options.currentPage + 2)) {
                paginationHTML += `
                    <li class="page-item ${i === this.options.currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${i}">${i}</a>
                    </li>
                `;
            } else if (i === this.options.currentPage - 3 || i === this.options.currentPage + 3) {
                paginationHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        // 下一页
        paginationHTML += `
            <li class="page-item ${this.options.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.options.currentPage + 1}">下一页</a>
            </li>
        `;

        pagination.innerHTML = paginationHTML;

        // 绑定分页事件
        pagination.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                if (page && page !== this.options.currentPage) {
                    this.options.currentPage = page;
                    this.render();
                }
            });
        });
    }

    editProject(projectId) {
        window.location.href = `/tour_projects/edit/${projectId}`;
    }

    viewProject(projectId) {
        window.location.href = `/tour_projects/detail/${projectId}`;
    }

    async deleteProject(projectId) {
        if (!confirm('确定要删除这个项目吗？')) {
            return;
        }

        try {
            const response = await fetch(`/tour_projects/delete/${projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.showSuccess('项目删除成功');
                this.loadProjects();
            } else {
                this.showError(result.message || '删除失败');
            }
        } catch (error) {
            console.error('删除项目失败:', error);
            this.showError('删除失败，请稍后重试');
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    showSuccess(message) {
        // 显示成功消息
        this.showMessage(message, 'success');
    }

    showError(message) {
        // 显示错误消息
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.container.insertBefore(messageDiv, this.container.firstChild);
        
        // 自动消失
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
}
```

### 1.2 ProjectCard 组件实现

#### HTML 模板结构
```html
<!-- ProjectCard 组件模板 -->
<div class="project-card" data-project-id="{{ project.id }}">
    <div class="card-header">
        <div class="project-title">
            <h5>{{ project.project_name }}</h5>
            <span class="project-hid">{{ project.project_hid }}</span>
        </div>
        <div class="status-badge status-{{ project.project_status }}">
            {{ project.project_status }}
        </div>
    </div>
    
    <div class="card-body">
        <div class="project-info">
            <div class="info-item">
                <label>联系人:</label>
                <span>{{ project.contact_person }}</span>
            </div>
            <div class="info-item">
                <label>联系方式:</label>
                <span>{{ project.contact_info }}</span>
            </div>
            <div class="info-item">
                <label>创建时间:</label>
                <span>{{ project.created_at.strftime('%Y-%m-%d') }}</span>
            </div>
        </div>
    </div>
    
    <div class="card-footer">
        <div class="action-buttons">
            <button class="btn btn-sm btn-primary edit-project" 
                    data-project-id="{{ project.id }}">
                编辑
            </button>
            <button class="btn btn-sm btn-info view-project" 
                    data-project-id="{{ project.id }}">
                查看
            </button>
            <button class="btn btn-sm btn-danger delete-project" 
                    data-project-id="{{ project.id }}">
                删除
            </button>
        </div>
    </div>
</div>
```

#### JavaScript 组件类
```javascript
class ProjectCard {
    constructor(element, options = {}) {
        this.element = element;
        this.options = options;
        this.projectId = this.element.dataset.projectId;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // 编辑按钮
        this.element.querySelector('.edit-project').addEventListener('click', (e) => {
            e.preventDefault();
            this.editProject();
        });

        // 查看按钮
        this.element.querySelector('.view-project').addEventListener('click', (e) => {
            e.preventDefault();
            this.viewProject();
        });

        // 删除按钮
        this.element.querySelector('.delete-project').addEventListener('click', (e) => {
            e.preventDefault();
            this.deleteProject();
        });

        // 卡片悬停效果
        this.element.addEventListener('mouseenter', () => {
            this.element.classList.add('hover');
        });

        this.element.addEventListener('mouseleave', () => {
            this.element.classList.remove('hover');
        });
    }

    editProject() {
        window.location.href = `/tour_projects/edit/${this.projectId}`;
    }

    viewProject() {
        window.location.href = `/tour_projects/detail/${this.projectId}`;
    }

    async deleteProject() {
        if (!confirm('确定要删除这个项目吗？')) {
            return;
        }

        try {
            const response = await fetch(`/tour_projects/delete/${this.projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.element.remove();
                this.showSuccess('项目删除成功');
            } else {
                this.showError(result.message || '删除失败');
            }
        } catch (error) {
            console.error('删除项目失败:', error);
            this.showError('删除失败，请稍后重试');
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
}
```

## 2. Itinerary Components 实现示例

### 2.1 ItineraryList 组件实现

#### HTML 模板结构
```html
<!-- ItineraryList 组件模板 -->
<div class="itinerary-list-container" id="itineraryList">
    <div class="list-header">
        <h3>行程管理</h3>
        <button class="btn btn-primary add-itinerary-btn">
            <i class="fas fa-plus"></i> 添加行程
        </button>
    </div>
    
    <div class="itinerary-table-container">
        <table class="itinerary-table">
            <thead>
                <tr>
                    <th>天数</th>
                    <th>日期标题</th>
                    <th>日期</th>
                    <th>行程内容</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="itineraryTableBody">
                <!-- 动态生成行程行 -->
            </tbody>
        </table>
    </div>
    
    <div class="empty-state" id="emptyState" style="display: none;">
        <i class="fas fa-route"></i>
        <h4>暂无行程</h4>
        <p>点击"添加行程"开始创建您的行程安排</p>
    </div>
</div>
```

#### JavaScript 组件类
```javascript
class ItineraryList {
    constructor(containerId, projectId, options = {}) {
        this.container = document.getElementById(containerId);
        this.projectId = projectId;
        this.options = options;
        this.state = {
            itineraries: [],
            loading: false
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadItineraries();
    }

    bindEvents() {
        // 添加行程按钮
        this.container.querySelector('.add-itinerary-btn').addEventListener('click', () => {
            this.showAddItineraryModal();
        });
    }

    async loadItineraries() {
        this.setState({ loading: true });
        
        try {
            const response = await fetch(`/api/projects/${this.projectId}/itineraries`);
            const data = await response.json();
            this.setState({ itineraries: data.itineraries });
        } catch (error) {
            console.error('加载行程失败:', error);
            this.showError('加载行程失败，请稍后重试');
        } finally {
            this.setState({ loading: false });
        }
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.render();
    }

    render() {
        if (this.state.loading) {
            this.showLoading();
            return;
        }

        if (this.state.itineraries.length === 0) {
            this.showEmptyState();
            return;
        }

        this.renderTable();
    }

    showLoading() {
        const tbody = this.container.querySelector('#itineraryTableBody');
        const emptyState = this.container.querySelector('#emptyState');
        
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                </td>
            </tr>
        `;
        emptyState.style.display = 'none';
    }

    showEmptyState() {
        const tbody = this.container.querySelector('#itineraryTableBody');
        const emptyState = this.container.querySelector('#emptyState');
        
        tbody.innerHTML = '';
        emptyState.style.display = 'block';
    }

    renderTable() {
        const tbody = this.container.querySelector('#itineraryTableBody');
        const emptyState = this.container.querySelector('#emptyState');
        
        tbody.innerHTML = this.state.itineraries.map((itinerary, index) => `
            <tr data-itinerary-id="${itinerary.id}">
                <td>第${index + 1}天</td>
                <td>${itinerary.day_title}</td>
                <td>${itinerary.date}</td>
                <td>${this.truncateContent(itinerary.content)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary edit-itinerary" 
                                data-itinerary-id="${itinerary.id}">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-danger delete-itinerary" 
                                data-itinerary-id="${itinerary.id}">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        emptyState.style.display = 'none';
        this.bindRowEvents();
    }

    bindRowEvents() {
        // 编辑行程
        this.container.querySelectorAll('.edit-itinerary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const itineraryId = e.target.dataset.itineraryId;
                this.editItinerary(itineraryId);
            });
        });

        // 删除行程
        this.container.querySelectorAll('.delete-itinerary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const itineraryId = e.target.dataset.itineraryId;
                this.deleteItinerary(itineraryId);
            });
        });
    }

    truncateContent(content, maxLength = 100) {
        if (content.length <= maxLength) {
            return content;
        }
        return content.substring(0, maxLength) + '...';
    }

    showAddItineraryModal() {
        const modal = new ItineraryModal({
            mode: 'add',
            projectId: this.projectId,
            onSave: (itinerary) => {
                this.addItinerary(itinerary);
            }
        });
        modal.show();
    }

    editItinerary(itineraryId) {
        const itinerary = this.state.itineraries.find(i => i.id == itineraryId);
        if (!itinerary) return;

        const modal = new ItineraryModal({
            mode: 'edit',
            itinerary: itinerary,
            projectId: this.projectId,
            onSave: (updatedItinerary) => {
                this.updateItinerary(itineraryId, updatedItinerary);
            }
        });
        modal.show();
    }

    async addItinerary(itineraryData) {
        try {
            const response = await fetch(`/api/projects/${this.projectId}/itineraries`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(itineraryData)
            });

            const result = await response.json();
            if (result.success) {
                this.showSuccess('行程添加成功');
                this.loadItineraries();
            } else {
                this.showError(result.message || '添加失败');
            }
        } catch (error) {
            console.error('添加行程失败:', error);
            this.showError('添加失败，请稍后重试');
        }
    }

    async updateItinerary(itineraryId, itineraryData) {
        try {
            const response = await fetch(`/api/itineraries/${itineraryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(itineraryData)
            });

            const result = await response.json();
            if (result.success) {
                this.showSuccess('行程更新成功');
                this.loadItineraries();
            } else {
                this.showError(result.message || '更新失败');
            }
        } catch (error) {
            console.error('更新行程失败:', error);
            this.showError('更新失败，请稍后重试');
        }
    }

    async deleteItinerary(itineraryId) {
        if (!confirm('确定要删除这个行程吗？')) {
            return;
        }

        try {
            const response = await fetch(`/api/itineraries/${itineraryId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.showSuccess('行程删除成功');
                this.loadItineraries();
            } else {
                this.showError(result.message || '删除失败');
            }
        } catch (error) {
            console.error('删除行程失败:', error);
            this.showError('删除失败，请稍后重试');
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.container.insertBefore(messageDiv, this.container.firstChild);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
}
```

### 2.2 ItineraryModal 组件实现

#### HTML 模板结构
```html
<!-- ItineraryModal 组件模板 -->
<div class="modal fade" id="itineraryModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="modalTitle">编辑行程</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="itineraryForm">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="dayTitle" class="form-label">日期标题</label>
                                <input type="text" class="form-control" id="dayTitle" name="day_title" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="date" class="form-label">日期</label>
                                <input type="date" class="form-control" id="date" name="date" required>
                            </div>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="content" class="form-label">行程内容</label>
                        <textarea class="form-control" id="content" name="content" rows="5" required></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                <button type="button" class="btn btn-primary" id="saveBtn">保存</button>
            </div>
        </div>
    </div>
</div>
```

#### JavaScript 组件类
```javascript
class ItineraryModal {
    constructor(options = {}) {
        this.options = {
            mode: 'add', // 'add' 或 'edit'
            projectId: null,
            itinerary: null,
            onSave: null,
            ...options
        };
        this.modal = null;
        this.form = null;
        this.init();
    }

    init() {
        this.createModal();
        this.bindEvents();
    }

    createModal() {
        // 创建模态框HTML
        const modalHTML = `
            <div class="modal fade" id="itineraryModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${this.options.mode === 'add' ? '添加行程' : '编辑行程'}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="itineraryForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="dayTitle" class="form-label">日期标题</label>
                                            <input type="text" class="form-control" id="dayTitle" name="day_title" required>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="date" class="form-label">日期</label>
                                            <input type="date" class="form-control" id="date" name="date" required>
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="content" class="form-label">行程内容</label>
                                    <textarea class="form-control" id="content" name="content" rows="5" required></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" id="saveBtn">保存</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        this.modal = new bootstrap.Modal(document.getElementById('itineraryModal'));
        this.form = document.getElementById('itineraryForm');
    }

    bindEvents() {
        // 保存按钮事件
        document.getElementById('saveBtn').addEventListener('click', () => {
            this.saveItinerary();
        });

        // 模态框关闭事件
        document.getElementById('itineraryModal').addEventListener('hidden.bs.modal', () => {
            this.destroy();
        });

        // 表单提交事件
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveItinerary();
        });
    }

    show() {
        if (this.options.mode === 'edit' && this.options.itinerary) {
            this.populateForm(this.options.itinerary);
        } else {
            this.clearForm();
        }
        this.modal.show();
    }

    populateForm(itinerary) {
        this.form.querySelector('#dayTitle').value = itinerary.day_title || '';
        this.form.querySelector('#date').value = itinerary.date || '';
        this.form.querySelector('#content').value = itinerary.content || '';
    }

    clearForm() {
        this.form.reset();
    }

    async saveItinerary() {
        if (!this.form.checkValidity()) {
            this.form.reportValidity();
            return;
        }

        const formData = new FormData(this.form);
        const itineraryData = {
            day_title: formData.get('day_title'),
            date: formData.get('date'),
            content: formData.get('content')
        };

        try {
            if (this.options.onSave) {
                await this.options.onSave(itineraryData);
                this.modal.hide();
            }
        } catch (error) {
            console.error('保存行程失败:', error);
            this.showError('保存失败，请稍后重试');
        }
    }

    showError(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const modalBody = document.querySelector('#itineraryModal .modal-body');
        modalBody.insertBefore(alertDiv, modalBody.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }

    destroy() {
        if (this.modal) {
            this.modal.dispose();
        }
        const modalElement = document.getElementById('itineraryModal');
        if (modalElement) {
            modalElement.remove();
        }
    }
}
```

## 3. 组件使用示例

### 3.1 初始化组件
```javascript
// 页面加载完成后初始化组件
document.addEventListener('DOMContentLoaded', function() {
    // 初始化项目列表
    const projectList = new ProjectList('projectList', {
        pageSize: 10
    });

    // 初始化项目卡片（如果有的话）
    document.querySelectorAll('.project-card').forEach(card => {
        new ProjectCard(card);
    });

    // 初始化行程列表
    const projectId = document.querySelector('#itineraryList')?.dataset.projectId;
    if (projectId) {
        const itineraryList = new ItineraryList('itineraryList', projectId);
    }
});
```

### 3.2 CSS 样式示例
```css
/* ProjectList 样式 */
.project-list-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.filter-bar {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
}

.filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.project-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

.project-table th,
.project-table td {
    padding: 12px;
    border: 1px solid #dee2e6;
    text-align: left;
}

.project-table th {
    background: #f8f9fa;
    font-weight: 600;
}

.status-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.status-处理中 { background: #fff3cd; color: #856404; }
.status-待出行 { background: #d1ecf1; color: #0c5460; }
.status-已完成 { background: #d4edda; color: #155724; }
.status-忽略单 { background: #f8d7da; color: #721c24; }

/* ProjectCard 样式 */
.project-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    transition: all 0.3s ease;
}

.project-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.card-header {
    padding: 15px;
    border-bottom: 1px solid #dee2e6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-body {
    padding: 15px;
}

.card-footer {
    padding: 15px;
    border-top: 1px solid #dee2e6;
    background: #f8f9fa;
}

/* ItineraryList 样式 */
.itinerary-list-container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
}

.list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.itinerary-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

.itinerary-table th,
.itinerary-table td {
    padding: 12px;
    border: 1px solid #dee2e6;
    text-align: left;
}

.empty-state {
    text-align: center;
    padding: 40px;
    color: #6c757d;
}

.empty-state i {
    font-size: 48px;
    margin-bottom: 16px;
    color: #dee2e6;
}
```

这些实现示例展示了如何将现有的HTML模板转换为可复用的JavaScript组件，提供了清晰的组件边界、事件处理和状态管理。 