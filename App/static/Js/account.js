// 全局变量存储账号数据和筛选条件
let accounts = [];
let currentFilters = {
    category: 'all',
    country: 'all',
    owner: 'all',
    search: ''
};
let currentPage = 1;
const itemsPerPage = 10;

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，开始初始化...');
    initializeApp();
});

// 初始化应用
async function initializeApp() {
    try {
        await loadCategories();
        await loadAccounts();
        initializeFilters();
        setupSearchListener();
    } catch (error) {
        console.error('初始化应用失败:', error);
    }
}

// 设置搜索监听器
function setupSearchListener() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            currentFilters.search = e.target.value.toLowerCase();
            renderAccounts();
        });
    }
}

// 加载账号数据
async function loadAccounts() {
    try {
        const response = await fetch('/api/accounts');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
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
        console.log('开始加载类别...');
        const response = await fetch('/api/categories');
        if (!response.ok) {
            throw new Error(`加载类别失败: ${response.status}`);
        }
        const categories = await response.json();
        console.log('获取到的类别:', categories);
        
        // 添加类别过滤按钮
        const categoryFilter = document.getElementById('categoryFilter');
        if (!categoryFilter) {
            console.warn('未找到类别过滤器元素');
            return;
        }

        categoryFilter.innerHTML = '';
        
        // 添加"全部"按钮
        const allButton = document.createElement('button');
        allButton.className = 'category-btn active';
        allButton.textContent = '全部';
        allButton.dataset.category = 'all';
        allButton.onclick = () => filterByCategory('all');
        categoryFilter.appendChild(allButton);
        
        // 添加类别按钮
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'category-btn';
            button.textContent = category;
            button.dataset.category = category;
            button.onclick = () => filterByCategory(category);
            categoryFilter.appendChild(button);
        });
        console.log('类别过滤器更新完成');

    } catch (error) {
        console.error('加载类别失败:', error);
        showErrorMessage('加载类别失败');
    }
}

// 显示错误消息
function showErrorMessage(message) {
    const container = document.querySelector('.container');
    if (!container) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-error';
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '20px';
    errorDiv.style.right = '20px';
    errorDiv.style.backgroundColor = '#f44336';
    errorDiv.style.color = 'white';
    errorDiv.style.padding = '10px 20px';
    errorDiv.style.borderRadius = '4px';
    errorDiv.style.zIndex = '1000';
    errorDiv.textContent = message;

    container.appendChild(errorDiv);

    setTimeout(() => {
        errorDiv.remove();
    }, 3000);
}

// 初始化筛选器
function initializeFilters() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = '';
        currentFilters.search = '';
    }
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

    // 更新总记录数
    const totalItems = filteredAccounts.length;
    document.getElementById('totalItems').textContent = totalItems;

    // 计算总页数
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    // 确保当前页码有效
    if (currentPage > totalPages) {
        currentPage = totalPages || 1;
    }

    // 计算当前页的数据范围
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
    
    // 获取当前页的数据
    const currentPageAccounts = filteredAccounts.slice(startIndex, endIndex);

    // 渲染账号列表
    const accountList = document.getElementById('accountList');
    accountList.innerHTML = currentPageAccounts.map(account => `
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
                <button class="btn btn-small" onclick="editAccount(${account.id})">编辑</button>
                <button class="btn btn-small btn-danger" onclick="deleteAccount(${account.id})">删除</button>
            </td>
        </tr>
    `).join('');

    // 更新分页控件
    updatePagination(totalPages);
}

// 更新分页控件
function updatePagination(totalPages) {
    const pageNumbers = document.getElementById('pageNumbers');
    if (!pageNumbers) return;

    let paginationHtml = '';
    
    // 生成页码按钮
    if (totalPages <= 7) {
        // 如果总页数较少，显示所有页码
        for (let i = 1; i <= totalPages; i++) {
            paginationHtml += `<button class="btn-page ${i === currentPage ? 'active' : ''}" 
                                     onclick="changePage(${i})">${i}</button>`;
        }
    } else {
        // 如果总页数较多，显示部分页码
        paginationHtml += `<button class="btn-page ${currentPage === 1 ? 'active' : ''}" 
                                 onclick="changePage(1)">1</button>`;
        
        if (currentPage > 3) {
            paginationHtml += '<span class="ellipsis">...</span>';
        }
        
        // 显示当前页码周围的页码
        for (let i = Math.max(2, currentPage - 2); i <= Math.min(totalPages - 1, currentPage + 2); i++) {
            paginationHtml += `<button class="btn-page ${i === currentPage ? 'active' : ''}" 
                                     onclick="changePage(${i})">${i}</button>`;
        }
        
        if (currentPage < totalPages - 2) {
            paginationHtml += '<span class="ellipsis">...</span>';
        }
        
        paginationHtml += `<button class="btn-page ${currentPage === totalPages ? 'active' : ''}" 
                                 onclick="changePage(${totalPages})">${totalPages}</button>`;
    }
    
    pageNumbers.innerHTML = paginationHtml;
    
    // 更新上一页/下一页按钮状态
    const prevButton = document.querySelector('.btn-page[onclick="changePage(\'prev\')"]');
    const nextButton = document.querySelector('.btn-page[onclick="changePage(\'next\')"]');
    
    if (prevButton) {
        prevButton.disabled = currentPage === 1;
        prevButton.classList.toggle('disabled', currentPage === 1);
    }
    if (nextButton) {
        nextButton.disabled = currentPage === totalPages;
        nextButton.classList.toggle('disabled', currentPage === totalPages);
    }
}

// 切换页码
function changePage(page) {
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
    
    const totalPages = Math.ceil(filteredAccounts.length / itemsPerPage);
    
    if (page === 'prev') {
        if (currentPage > 1) {
            currentPage--;
        }
    } else if (page === 'next') {
        if (currentPage < totalPages) {
            currentPage++;
        }
    } else {
        currentPage = parseInt(page);
    }
    
    renderAccounts();
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
    // 如果没有找到现有的 alert 元素，创建一个新的
    let alert = document.getElementById('formAlert');
    if (!alert) {
        alert = document.createElement('div');
        alert.id = 'formAlert';
        document.querySelector('.container').appendChild(alert);
    }
    
    alert.textContent = message;
    alert.className = `alert ${isSuccess ? 'alert-success' : 'alert-error'}`;
    alert.style.display = 'block';
    
    // 添加基本样式
    alert.style.position = 'fixed';
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.padding = '10px 20px';
    alert.style.borderRadius = '4px';
    alert.style.zIndex = '1000';
    
    if (isSuccess) {
        alert.style.backgroundColor = '#4caf50';
        alert.style.color = 'white';
    } else {
        alert.style.backgroundColor = '#f44336';
        alert.style.color = 'white';
    }
    
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