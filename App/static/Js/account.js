// 全局变量存储账号数据和筛选条件
let accounts = [];
let currentFilters = {
    category: 'all',
    country: 'all',
    owner: 'all',
    search: ''
};

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    loadAccounts();
    initializeFilters();
    setupEventListeners();
    
    // 添加编辑表单提交处理
    const editForm = document.getElementById('editForm');
    editForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        await submitEditForm();
    });
});

// 加载账号数据
async function loadAccounts() {
    try {
        const response = await fetch('/api/accounts');
        accounts = await response.json();
        updateFilters();
        renderAccounts();
    } catch (error) {
        console.error('加载账号数据失败:', error);
        showAlert('加载账号数据失败', false);
    }
}

// 加载类别
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();
        
        // 添加到新建表单
        const categorySelect = document.getElementById('category');
        categorySelect.innerHTML = '<option value="">请选择类别...</option>';
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            categorySelect.appendChild(option);
        });

        // 添加到编辑表单
        const editCategorySelect = document.getElementById('editCategory');
        editCategorySelect.innerHTML = '<option value="">请选择类别...</option>';
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            editCategorySelect.appendChild(option);
        });

        // 添加类别过滤按钮
        const categoryFilter = document.getElementById('categoryFilter');
        categoryFilter.innerHTML = '<button class="category-btn active" data-category="all">全部</button>';
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'category-btn';
            button.textContent = category;
            button.dataset.category = category;
            button.onclick = () => filterByCategory(category);
            categoryFilter.appendChild(button);
        });
    } catch (error) {
        console.error('加载类别失败:', error);
        showAlert('加载类别失败', false);
    }
}

// 初始化筛选器
function initializeFilters() {
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', function(e) {
        currentFilters.search = e.target.value.toLowerCase();
        renderAccounts();
    });
}

// 更新筛选选项
function updateFilters() {
    // 获取唯一的国家和账户归属
    const countries = ['all', ...new Set(accounts.map(a => a.country).filter(Boolean))];
    const owners = ['all', ...new Set(accounts.map(a => a.owner).filter(Boolean))];

    // 更新筛选按钮
    updateFilterButtons('countryFilter', countries, 'country');
    updateFilterButtons('ownerFilter', owners, 'owner');
}

// 更新筛选按钮
function updateFilterButtons(containerId, items, filterType) {
    const container = document.getElementById(containerId);
    container.innerHTML = items.map(item => `
        <button class="category-btn ${item === 'all' ? 'active' : ''}" 
                data-${filterType}="${item}">
            ${item === 'all' ? '全部' : item}
        </button>
    `).join('');

    // 添加点击事件
    container.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除同组其他按钮的active类
            container.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            // 添加当前按钮的active类
            this.classList.add('active');
            // 更新筛选条件
            currentFilters[filterType] = this.dataset[filterType];
            renderAccounts();
        });
    });
}

// 筛选函数
function filterByCategory(category) {
    const buttons = document.querySelectorAll('#categoryFilter .category-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.category === category) {
            btn.classList.add('active');
        }
    });
    currentFilters.category = category;
    renderAccounts();
}

// 渲染账号列表
function renderAccounts() {
    const filteredAccounts = accounts.filter(account => {
        const matchesCategory = currentFilters.category === 'all' || account.category === currentFilters.category;
        const matchesCountry = currentFilters.country === 'all' || account.country === currentFilters.country;
        const matchesOwner = currentFilters.owner === 'all' || account.owner === currentFilters.owner;
        const matchesSearch = !currentFilters.search || 
            account.platform.toLowerCase().includes(currentFilters.search) ||
            account.username.toLowerCase().includes(currentFilters.search) ||
            (account.description && account.description.toLowerCase().includes(currentFilters.search));

        return matchesCategory && matchesCountry && matchesOwner && matchesSearch;
    });

    const accountList = document.getElementById('accountList');
    accountList.innerHTML = filteredAccounts.map(account => `
        <tr>
            <td>
                ${account.platform}
                ${account.website_url ? `<br><a href="${account.website_url}" target="_blank">${account.website_url}</a>` : ''}
            </td>
            <td>${account.category || ''}</td>
            <td>${account.owner || ''}</td>
            <td>${account.username}</td>
            <td>
                <div class="password-container">
                    <div class="password-field">
                        <span>••••••••</span>
                    </div>
                    <div class="password-actions">
                        <button class="btn-small" onclick="togglePassword(this, '${account.password}')">显示</button>
                    </div>
                </div>
            </td>
            <td>${account.country ? account.country + (account.region ? ' - ' + account.region : '') : ''}</td>
            <td>
                <button class="btn" onclick="editAccount(${account.id})">编辑</button>
                <button class="btn btn-danger" onclick="deleteAccount(${account.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

// 切换密码显示/隐藏
function togglePassword(button, password) {
    const passwordContainer = button.closest('.password-container');
    const passwordField = passwordContainer.querySelector('.password-field');
    const passwordActions = passwordContainer.querySelector('.password-actions');
    
    if (button.textContent === '显示') {
        passwordField.innerHTML = `<span>${password}</span>`;
        passwordActions.innerHTML = `
            <button class="btn-small" onclick="togglePassword(this, '${password}')">隐藏</button>
            <button class="btn-small" onclick="copyPassword('${password}')">复制</button>
        `;
    } else {
        passwordField.innerHTML = `<span>••••••••</span>`;
        passwordActions.innerHTML = `
            <button class="btn-small" onclick="togglePassword(this, '${password}')">显示</button>
        `;
    }
}

// 复制密码到剪贴板
async function copyPassword(password) {
    try {
        await navigator.clipboard.writeText(password);
        showAlert('密码已复制到剪贴板', true);
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 编辑账号
async function editAccount(id) {
    const account = accounts.find(a => a.id === id);
    if (!account) return;

    try {
        // 加载类别选项
        const response = await fetch('/api/categories');
        const categories = await response.json();
        
        // 填充类别选择器
        const editCategorySelect = document.getElementById('editCategory');
        editCategorySelect.innerHTML = `
            <option value="">请选择类别...</option>
            ${categories.map(category => `
                <option value="${category}" ${account.category === category ? 'selected' : ''}>
                    ${category}
                </option>
            `).join('')}
        `;

        // 填充编辑表单
        document.getElementById('editId').value = account.id;
        document.getElementById('editPlatform').value = account.platform;
        document.getElementById('editWebsiteUrl').value = account.website_url || '';
        document.getElementById('editCategory').value = account.category || '';
        document.getElementById('editOwner').value = account.owner || '';
        document.getElementById('editUsername').value = account.username;
        document.getElementById('editPassword').value = account.password;
        document.getElementById('editCountry').value = account.country || '';
        document.getElementById('editRegion').value = account.region || '';
        document.getElementById('editDescription').value = account.description || '';
        document.getElementById('editNotes').value = account.notes || '';

        // 显示模态框
        document.getElementById('editModal').style.display = 'block';
    } catch (error) {
        console.error('加载类别失败:', error);
        showAlert('加载类别失败', false);
    }
}

// 关闭编辑模态框
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// 删除账号
async function deleteAccount(id) {
    if (!confirm('确定要删除这个账号吗？')) return;

    try {
        const response = await fetch(`/api/accounts/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showAlert('账号删除成功', true);
            loadAccounts(); // 重新加载账号列表
        } else {
            const data = await response.json();
            showAlert(data.error || '删除失败', false);
        }
    } catch (error) {
        console.error('删除账号失败:', error);
        showAlert('删除账号失败', false);
    }
}

// 显示提示信息
function showAlert(message, isSuccess) {
    const alert = document.getElementById('formAlert');
    alert.textContent = message;
    alert.className = `alert ${isSuccess ? 'alert-success' : 'alert-error'}`;
    alert.style.display = 'block';
    setTimeout(() => {
        alert.style.display = 'none';
    }, 3000);
}

// 提交编辑表单
async function submitEditForm() {
    const accountId = document.getElementById('editId').value;
    const formData = {
        platform: document.getElementById('editPlatform').value,
        website_url: document.getElementById('editWebsiteUrl').value,
        category: document.getElementById('editCategory').value,
        owner: document.getElementById('editOwner').value,
        username: document.getElementById('editUsername').value,
        country: document.getElementById('editCountry').value,
        region: document.getElementById('editRegion').value,
        description: document.getElementById('editDescription').value,
        notes: document.getElementById('editNotes').value
    };

    // 只有当密码字段有值时才包含密码
    const password = document.getElementById('editPassword').value;
    if (password.trim()) {
        formData.password = password;
    }

    try {
        const response = await fetch(`/api/accounts/${accountId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (response.ok) {
            showAlert('账号更新成功', true);
            closeEditModal();
            await loadAccounts(); // 重新加载账号列表
        } else {
            showAlert(data.error || '更新失败', false);
            console.error('更新失败:', data.error);
        }
    } catch (error) {
        console.error('更新账号时发生错误:', error);
        showAlert('更新账号失败: ' + error.message, false);
    }
} 