// 全局变量存储账号数据和筛选条件
let accounts = [];
let currentFilters = {
    category: '',
    country: '',
    owner: '',
    search: ''
};
let currentPage = 1;
const itemsPerPage = 10;

// 初始化页面
document.addEventListener('DOMContentLoaded', async function() {
    console.log('页面加载完成，开始初始化...');
    await initializeApp();
});

// 初始化应用
async function initializeApp() {
    try {
        console.log('开始初始化应用...');
        
        // 等待DOM完全加载
        if (document.readyState !== 'complete') {
            await new Promise(resolve => {
                window.addEventListener('load', resolve);
            });
        }

        console.log('DOM加载完成，开始初始化组件...');

        // 获取并检查所有筛选器元素
        const selectors = {
            category: document.getElementById('categorySelect'),
            country: document.getElementById('countrySelect'),
            owner: document.getElementById('ownerSelect'),
            search: document.getElementById('searchInput')
        };

        // 检查并记录选择器状态
        Object.entries(selectors).forEach(([key, selector]) => {
            if (!selector) {
                console.error(`未找到${key}选择器，DOM结构:`, document.body.innerHTML);
                throw new Error(`关键选择器未找到: ${key}`);
            }
            console.log(`${key}选择器已找到:`, selector);
        });

        // 设置搜索监听器
        if (selectors.search) {
            selectors.search.addEventListener('input', function(e) {
                currentFilters.search = e.target.value.toLowerCase();
                renderAccounts();
            });
        }

        // 并行加载数据
        console.log('开始并行加载数据...');
        await Promise.all([
            loadAccounts(),
            loadCategories(),
            loadPopularWebsites()
        ]);
        
        console.log('应用初始化完成');
    } catch (error) {
        console.error('应用初始化失败:', error);
        showAlert('初始化失败: ' + error.message, false);
    }
}

// 加载账号数据
async function loadAccounts() {
    try {
        console.log('%c开始加载账号数据...', 'color: blue; font-weight: bold');
        
        // 获取账号数据
        const response = await fetch('/api/accounts');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('%c获取到的原始数据:', 'color: green', data);
        
        if (!data.success) {
            throw new Error(data.message || '加载账号失败');
        }
        
        if (!Array.isArray(data.accounts)) {
            console.error('账号数据不是数组:', data);
            throw new Error('账号数据格式错误');
        }

        // 更新全局账号数据
        accounts = data.accounts;
        console.log('%c账号数据总数:', 'color: blue', accounts.length);

        // 更新筛选器
        await updateFilters(accounts);

        // 渲染账号列表
        renderAccounts();
        
        console.log('%c账号数据加载和筛选器更新完成', 'color: green; font-weight: bold');
        return data.accounts;
    } catch (error) {
        console.error('加载账号数据失败:', error);
        showAlert('加载账号数据失败: ' + error.message, false);
        throw error;
    }
}

// 加载类别数据
async function loadCategories() {
    try {
        console.log('开始加载类别数据...');
        const response = await fetch('/api/categories');
        console.log('类别API响应:', response);
        
        if (!response.ok) {
            if (response.status === 404) {
                console.log('类别API未找到，将使用账号数据中的类别');
                // 从账号数据中提取类别
                const categories = [...new Set(accounts.map(acc => acc.category || '未分类'))].filter(Boolean).sort();
                return categories;
            }
            throw new Error(`加载类别失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('获取到的类别数据:', data);
        
        if (!data.success || !Array.isArray(data.categories)) {
            throw new Error('类别数据格式错误');
        }

        const categories = data.categories;
        console.log('解析后的类别数据:', categories);

        // 获取所有类别选择器
        const categorySelectors = {
            categorySelect: document.getElementById('categorySelect'),     // 主页筛选器的类别选择器
            editCategory: document.getElementById('editCategory')          // 编辑表单的类别选择器
        };

        // 检查并记录选择器状态
        Object.entries(categorySelectors).forEach(([key, selector]) => {
            if (!selector) {
                console.error(`未找到${key}选择器，请检查HTML中的ID是否正确`);
            } else {
                console.log(`找到${key}选择器:`, selector);
                
                // 清空现有选项
                selector.innerHTML = key === 'categorySelect' 
                    ? '<option value="">全部类别</option>'
                    : '<option value="">请选择类别</option>';
                
                // 添加新选项
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
                    selector.appendChild(option);
                });
                
                console.log(`已更新${key}选择器，选项数量:`, selector.options.length);
            }
        });

        console.log('类别选择器更新完成');
        return categories;
    } catch (error) {
        console.error('加载类别失败:', error);
        showAlert('加载类别失败: ' + error.message, false);
        // 使用账号数据中的类别作为备选
        const categories = [...new Set(accounts.map(acc => acc.category || '未分类'))].filter(Boolean).sort();
        return categories;
    }
}

// 显示错误消息
function showErrorMessage(message) {
    const container = document.querySelector('.container');
    if (!container) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-error';
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

    // 重置所有筛选器的值
    const selectors = {
        category: document.getElementById('categorySelect'),
        country: document.getElementById('countrySelect'),
        owner: document.getElementById('ownerSelect')
    };

    Object.entries(selectors).forEach(([key, selector]) => {
        if (selector) {
            selector.value = '';
            currentFilters[key] = '';
        }
    });
}

// 渲染账号列表
function renderAccounts() {
    console.log('开始渲染账号列表...');
    console.log('当前筛选条件:', currentFilters);
    console.log('可用账号数据:', accounts);

    const filteredAccounts = accounts.filter(account => {
        const matchesCategory = !currentFilters.category || account.category === currentFilters.category;
        const matchesCountry = !currentFilters.country || account.country === currentFilters.country;
        const matchesOwner = !currentFilters.owner || account.owner === currentFilters.owner;
        const matchesSearch = !currentFilters.search || 
            (account.platform && account.platform.toLowerCase().includes(currentFilters.search.toLowerCase())) ||
            (account.username && account.username.toLowerCase().includes(currentFilters.search.toLowerCase())) ||
            (account.description && account.description.toLowerCase().includes(currentFilters.search.toLowerCase()));

        return matchesCategory && matchesCountry && matchesOwner && matchesSearch;
    });

    console.log('筛选后的账号数:', filteredAccounts.length);

    // 更新总记录数
    const totalItems = filteredAccounts.length;
    const totalItemsElement = document.getElementById('totalItems');
    if (totalItemsElement) {
        totalItemsElement.textContent = totalItems;
    }

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
    console.log('当前页显示的账号数:', currentPageAccounts.length);

    // 渲染账号列表
    const accountList = document.getElementById('accountList');
    if (!accountList) {
        console.error('未找到账号列表元素');
        return;
    }

    accountList.innerHTML = currentPageAccounts.map(account => renderAccountRow(account)).join('');

    // 添加点击事件监听器
    const platformCells = accountList.querySelectorAll('.platform-cell');
    platformCells.forEach(cell => {
        cell.addEventListener('click', function(e) {
            // 如果点击的是链接，不触发点击计数（因为链接有自己的点击处理）
            if (e.target.classList.contains('website-link')) {
                return;
            }
            const accountId = this.dataset.accountId;
            console.log('Platform cell clicked for account:', accountId);
            incrementClick(accountId);
        });
    });

    // 为所有网站链接添加点击事件
    const websiteLinks = accountList.querySelectorAll('.website-link');
    websiteLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const accountId = this.dataset.accountId;
            console.log('Website link clicked for account:', accountId);
            
            // 先增加点击次数
            incrementClick(accountId).then(() => {
                // 点击次数更新成功后，打开链接
                window.open(this.href, '_blank');
            }).catch(error => {
                console.error('Failed to increment click count:', error);
                // 即使点击次数更新失败，也打开链接
                window.open(this.href, '_blank');
            });
        });
    });

    // 更新分页控件
    updatePagination(totalPages);
}

function renderAccountRow(account) {
    return `
        <tr data-account-id="${account.id}">
            <td class="clickable">
                <div class="platform-cell" data-account-id="${account.id}">
                    <div class="platform-name">
                        ${account.website_url ? 
                            `<a href="#" onclick="visitWebsite('${account.website_url}', ${account.id}); return false;">${account.platform}</a>` 
                            : account.platform}
                    </div>
                    ${account.website_url ? 
                        `<div class="website-url">
                            <a href="#" onclick="visitWebsite('${account.website_url}', ${account.id}); return false;">${account.website_url}</a>
                        </div>` 
                        : ''}
                </div>
            </td>
            <td>${account.category || ''}</td>
            <td>${account.owner || ''}</td>
            <td>${account.username}</td>
            <td class="password-cell">
                <div class="password-container">
                    <span class="password-text">••••••••</span>
                    <div class="password-actions">
                        <button class="btn-small" onclick="togglePassword(this, '${account.password}')">
                            <i class="fas fa-eye"></i> 显示
                        </button>
                        <button class="btn-small copy-btn" onclick="copyPassword('${account.password}')" style="display: none;">
                            <i class="fas fa-copy"></i> 复制
                        </button>
                    </div>
                </div>
            </td>
            <td>${account.country ? account.country + (account.region ? '/' + account.region : '') : ''}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-secondary btn-sm" onclick="editAccount(${account.id})">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteAccount(${account.id})">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </div>
            </td>
        </tr>
    `;
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
    const passwordText = passwordContainer.querySelector('.password-text');
    const passwordActions = passwordContainer.querySelector('.password-actions');
    const copyButton = passwordActions.querySelector('button:last-child');
    
    if (button.textContent.includes('显示')) {
        passwordText.textContent = password;
        button.innerHTML = '<i class="fas fa-eye-slash"></i> 隐藏';
        copyButton.style.display = 'inline-flex';  // 显示复制按钮
    } else {
        passwordText.textContent = '••••••••';
        button.innerHTML = '<i class="fas fa-eye"></i> 显示';
        copyButton.style.display = 'none';  // 隐藏复制按钮
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

// 切换编辑表单中密码的显示/隐藏
function toggleEditPassword() {
    const passwordInput = document.getElementById('editPassword');
    const toggleButton = document.querySelector('.password-actions button');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.textContent = '隐藏密码';
    } else {
        passwordInput.type = 'password';
        toggleButton.textContent = '显示密码';
    }
}

// 复制编辑表单中的密码
async function copyEditPassword() {
    const passwordInput = document.getElementById('editPassword');
    try {
        await navigator.clipboard.writeText(passwordInput.value);
        showAlert('密码已复制到剪贴板', true);
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 编辑账号
async function editAccount(id) {
    try {
        console.log('开始编辑账号:', id);
        
        // 查找账号
        const account = accounts.find(a => a.id === id);
        if (!account) {
            throw new Error('未找到账号');
        }
        console.log('找到要编辑的账号:', account);
        
        // 填充编辑表单的基本信息
        document.getElementById('editId').value = account.id;
        document.getElementById('editPlatform').value = account.platform || '';
        document.getElementById('editWebsiteUrl').value = account.website_url || '';
        document.getElementById('editUsername').value = account.username || '';
        document.getElementById('editOwner').value = account.owner || '';
        document.getElementById('editCountry').value = account.country || '';
        document.getElementById('editRegion').value = account.region || '';
        document.getElementById('editDescription').value = account.description || '';
        document.getElementById('editNotes').value = account.notes || '';
        
        // 填充密码字段
        const passwordInput = document.getElementById('editPassword');
        if (passwordInput) {
            passwordInput.value = account.password || '';
            passwordInput.type = 'password'; // 确保密码是隐藏的
            const toggleButton = document.querySelector('.password-actions button');
            if (toggleButton) {
                toggleButton.textContent = '显示密码';
            }
        }
        
        console.log('基本信息已填充到表单');

        // 获取类别选择器
        const editCategorySelect = document.getElementById('editCategory');
        if (!editCategorySelect) {
            throw new Error('未找到类别选择器');
        }

        // 获取所有唯一的类别
        const categories = [...new Set(accounts.map(acc => acc.category || '未分类'))].filter(Boolean).sort();

        // 更新编辑表单的类别选择器
        editCategorySelect.innerHTML = `
            <option value="">请选择类别...</option>
            ${categories.map(category => `
                <option value="${category}" ${category === account.category ? 'selected' : ''}>
                    ${category}
                </option>
            `).join('')}
        `;

        // 显示模态框
        const editModal = document.getElementById('editModal');
        if (!editModal) {
            throw new Error('未找到编辑模态框');
        }
        
        // 使用Bootstrap的模态框方法
        const modal = new bootstrap.Modal(editModal);
        modal.show();
        
        console.log('编辑模态框已显示');

    } catch (error) {
        console.error('编辑账号失败:', error);
        showAlert('编辑账号失败: ' + error.message, false);
    }
}

// 提交编辑表单
async function submitEditForm() {
    try {
        console.log('开始提交编辑表单...');
        const id = document.getElementById('editId').value;
        if (!id) {
            throw new Error('账号ID不能为空');
        }

        // 收集表单数据
        const data = {
            platform: document.getElementById('editPlatform').value.trim(),
            website_url: document.getElementById('editWebsiteUrl').value.trim(),
            username: document.getElementById('editUsername').value.trim(),
            category: document.getElementById('editCategory').value,
            owner: document.getElementById('editOwner').value.trim(),
            country: document.getElementById('editCountry').value.trim(),
            region: document.getElementById('editRegion').value.trim(),
            description: document.getElementById('editDescription').value.trim(),
            notes: document.getElementById('editNotes').value.trim()
        };

        // 验证必填字段
        if (!data.platform) throw new Error('平台名称不能为空');
        if (!data.username) throw new Error('用户名不能为空');
        if (!data.category) throw new Error('请选择类别');

        console.log('表单数据:', data);

        // 检查密码字段
        const password = document.getElementById('editPassword').value;
        if (password.trim()) {
            data.password = password;
            console.log('包含新密码');
        }

        console.log('准备发送请求到:', `/api/accounts/${id}`);
        const response = await fetch(`/api/accounts/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        console.log('服务器响应状态:', response.status);
        const result = await response.json();
        console.log('服务器响应数据:', result);

        if (!response.ok) {
            throw new Error(result.message || `服务器错误: ${response.status}`);
        }

        if (result.success) {
            showAlert('账号更新成功', true);
            closeEditModal();
            await loadAccounts(); // 重新加载账号列表
            await loadPopularWebsites(); // 更新热门网站列表
        } else {
            throw new Error(result.message || '更新失败，但服务器没有提供具体原因');
        }
    } catch (error) {
        console.error('更新账号失败:', error);
        showAlert('更新账号失败: ' + error.message, false);
    }
}

// 关闭编辑模态框
function closeEditModal() {
    const editModal = document.getElementById('editModal');
    if (editModal) {
        // 使用Bootstrap的模态框方法关闭
        const modal = bootstrap.Modal.getInstance(editModal);
        if (modal) {
            modal.hide();
        }
        
        // 重置表单
        const form = document.getElementById('editAccountForm');
        if (form) {
            form.reset();
        }
        
        // 清空密码字段
        const passwordInput = document.getElementById('editPassword');
        if (passwordInput) {
            passwordInput.value = '';
        }
        
        // 手动移除背景遮罩层
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
        
        // 移除body上的modal-open类
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }
}

// 删除账号
async function deleteAccount(id) {
    if (!confirm('确定要删除这个账号吗？此操作不可恢复。')) return;

    try {
        console.log('开始删除账号:', id);
        showAlert('正在删除账号...', true);

        const response = await fetch(`/api/accounts/${id}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        console.log('删除请求响应状态:', response.status);
        
        // 检查响应的Content-Type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
        if (response.ok) {
                console.log('账号删除成功');
            showAlert('账号删除成功', true);
                await loadAccounts(); // 重新加载账号列表
                await loadPopularWebsites(); // 更新热门网站列表
            } else {
                throw new Error(data.message || '删除失败');
            }
        } else {
            // 如果响应不是JSON格式
            const text = await response.text();
            console.error('服务器返回非JSON响应:', text);
            throw new Error(`删除失败: 服务器返回状态码 ${response.status}`);
        }
    } catch (error) {
        console.error('删除账号时发生错误:', error);
        showAlert('删除账号失败: ' + (error.message || '未知错误'), false);
        
        // 如果是网络错误，显示更友好的提示
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            showAlert('网络错误，请检查您的网络连接后重试', false);
        }
    }
}

// 显示提示信息
function showAlert(message, isSuccess = true) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${isSuccess ? 'success' : 'danger'}`;
    alertDiv.innerHTML = `
        <i class="fas ${isSuccess ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        ${message}
    `;
    
    document.body.appendChild(alertDiv);
    
    // 1.5秒后自动消失
    setTimeout(() => {
        alertDiv.remove();
    }, 1500);
}

// 增加点击次数
async function incrementClick(accountId) {
    try {
        console.log('开始增加点击次数，账号ID:', accountId);
        const response = await fetch(`/api/accounts/increment_click/${accountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('服务器响应:', response);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('响应数据:', data);
        
        if (data.success) {
            // 更新热门网站列表
            await loadPopularWebsites();
            console.log('热门网站列表已更新');
        } else {
            throw new Error(data.message || '更新失败');
        }
    } catch (error) {
        console.error('更新点击次数时发生错误:', error);
        throw error; // 重新抛出错误以便调用者处理
    }
}

// 加载热门网站
async function loadPopularWebsites() {
    try {
        console.log('开始加载热门网站...');
        const popularWebsitesContainer = document.getElementById('popularWebsites');
        
        if (!popularWebsitesContainer) {
            console.error('未找到热门网站容器元素');
            return;
        }

        // 显示加载状态
        popularWebsitesContainer.innerHTML = `
            <div class="loading-state">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p>正在加载热门网站...</p>
            </div>
        `;

        // 从API获取热门网站数据
        console.log('正在从API获取热门网站数据...');
        const response = await fetch('/api/accounts/popular');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('获取到的热门网站数据:', data);

        if (!data.success) {
            throw new Error(data.message || '获取热门网站失败');
        }

        if (!Array.isArray(data.accounts)) {
            throw new Error('热门网站数据格式错误');
        }

        // 直接使用API返回的数据，不需要再次过滤
        const popularWebsites = data.accounts;
        console.log('解析后的热门网站数量:', popularWebsites.length);

        // 清空现有内容
        popularWebsitesContainer.innerHTML = '';

        // 如果没有热门网站
        if (popularWebsites.length === 0) {
            popularWebsitesContainer.innerHTML = `
                <div class="no-data-state">
                    <i class="fas fa-globe"></i>
                    <p>暂无热门网站数据</p>
                </div>
            `;
            return;
        }

        // 添加热门网站列表
        popularWebsites.forEach((website, index) => {
            // 确保网站数据完整
            if (website && website.website_url && website.platform) {
                const websiteElement = document.createElement('div');
                websiteElement.className = 'popular-item';
                websiteElement.innerHTML = `
                    <div class="website-rank">${index + 1}</div>
                    <a href="${website.website_url}" 
                       class="website-link" 
                       target="_blank" 
                       onclick="visitWebsite('${website.website_url}', ${website.id}); return false;">
                        ${website.platform}
                    </a>
                    <span class="click-count">${website.click_count || 0}次访问</span>
                `;
                popularWebsitesContainer.appendChild(websiteElement);
            }
        });

        console.log('热门网站加载完成，共显示', popularWebsites.length, '个网站');
    } catch (error) {
        console.error('加载热门网站失败:', error);
        const popularWebsitesContainer = document.getElementById('popularWebsites');
        if (popularWebsitesContainer) {
            popularWebsitesContainer.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>加载热门网站失败: ${error.message}</p>
                </div>
            `;
        }
    }
}

// 访问网站
async function visitWebsite(url, accountId) {
    try {
        // 先增加点击次数
        await incrementClick(accountId);
        // 然后在新标签页中打开网站
        window.open(url, '_blank');
    } catch (error) {
        console.error('访问网站失败:', error);
        // 即使点击次数更新失败，也打开网站
        window.open(url, '_blank');
    }
}

// 更新筛选器
async function updateFilters(accounts) {
    try {
        console.log('开始更新筛选器...', accounts);
        
        if (!Array.isArray(accounts) || accounts.length === 0) {
            console.error('无效的账号数据:', accounts);
            return;
        }

        // 获取所有筛选器元素
        const selectors = {
            category: document.getElementById('categorySelect'),
            country: document.getElementById('countrySelect'),
            owner: document.getElementById('ownerSelect')
        };

        // 检查筛选器元素
        Object.entries(selectors).forEach(([key, selector]) => {
            if (!selector) {
                throw new Error(`筛选器元素未找到: ${key}Select`);
            }
            console.log(`找到筛选器元素: ${key}Select，当前选项数:`, selector.options.length);
        });

        // 提取唯一值并排序
        const uniqueValues = {
            category: [...new Set(accounts.map(acc => (acc.category || '未分类').trim()))].filter(val => val).sort(),
            country: [...new Set(accounts.map(acc => (acc.country || '未知').trim()))].filter(val => val).sort(),
            owner: [...new Set(accounts.map(acc => (acc.owner || '未知').trim()))].filter(val => val).sort()
        };

        console.log('提取的筛选数据:', uniqueValues);

        // 更新每个选择器
        for (const [key, values] of Object.entries(uniqueValues)) {
            const selector = selectors[key];
            if (!selector) continue;

            // 保存当前选中的值
            const currentValue = selector.value;

            try {
                // 构建选项HTML
                const optionsHtml = `
                    <option value="">全部${key === 'category' ? '类别' : key === 'country' ? '国家' : '所有者'}</option>
                    ${values.map(value => `<option value="${value}">${value}</option>`).join('')}
                `;

                // 更新选择器的HTML
                selector.innerHTML = optionsHtml;
                console.log(`${key}选择器HTML已更新，新选项数:`, selector.options.length);

                // 恢复之前的选中值
                if (currentValue && values.includes(currentValue)) {
                    selector.value = currentValue;
                }

                // 添加事件监听器
                selector.addEventListener('change', function() {
                    console.log(`${key}选择器值改变:`, this.value);
                    currentFilters[key] = this.value;
                    renderAccounts();
                });

                console.log(`${key}选择器更新完成，选项数量:`, values.length + 1);
            } catch (error) {
                console.error(`更新${key}选择器时出错:`, error);
                throw error;
            }
        }

        console.log('所有筛选器更新完成');
    } catch (error) {
        console.error('更新筛选器失败:', error);
        throw error;
    }
}

// 下载Excel模板
async function downloadTemplate() {
    try {
        const response = await fetch('/api/accounts/download_template');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('content-disposition');
        let filename = '账号导入模板.xlsx';
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // 下载文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showAlert('模板下载成功', true);
    } catch (error) {
        console.error('下载模板失败:', error);
        showAlert('下载模板失败: ' + error.message, false);
    }
}

// 初始化事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // 添加下载模板按钮事件监听器
    const downloadTemplateBtn = document.getElementById('downloadTemplate');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', downloadTemplate);
    }
}); 