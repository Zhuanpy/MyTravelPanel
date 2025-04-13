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
    console.log('账号管理器 v2025.04.14 - 初始化...');
    
    // 初始化密码按钮状态
    initPasswordButtons();
    
    await initializeApp();
});

// 初始化密码按钮状态
function initPasswordButtons() {
    // 确保编辑模态框中的复制密码按钮一开始是隐藏的
    const editCopyButton = document.querySelector('#editModal .password-actions button:nth-child(2)');
    if (editCopyButton) {
        editCopyButton.style.display = 'none';
        console.log('初始化编辑密码复制按钮: 已隐藏');
    } else {
        console.error('无法找到编辑密码复制按钮');
    }
    
    // 确保添加模态框中的复制密码按钮一开始是隐藏的
    const addCopyButton = document.querySelector('#addAccountModal .password-actions button:nth-child(2)');
    if (addCopyButton) {
        addCopyButton.style.display = 'none';
        console.log('初始化添加密码复制按钮: 已隐藏');
    } else {
        console.error('无法找到添加密码复制按钮');
    }
    
    // 添加调试按钮
    document.addEventListener('keydown', function(e) {
        // 按下Ctrl+Alt+D触发调试
        if (e.ctrlKey && e.altKey && e.key === 'd') {
            debugPasswordButtons();
        }
    });
    
    console.log('密码按钮状态已初始化');
}

// 调试密码按钮
function debugPasswordButtons() {
    console.log('====== 密码按钮调试开始 ======');
    
    // 检查编辑模态框中的密码按钮
    const editModal = document.getElementById('editModal');
    if (editModal) {
        console.log('找到编辑模态框');
        const editActions = editModal.querySelector('.password-actions');
        if (editActions) {
            console.log('找到编辑密码按钮容器');
            const buttons = editActions.querySelectorAll('button');
            console.log(`找到 ${buttons.length} 个按钮`);
            buttons.forEach((btn, index) => {
                console.log(`按钮 ${index+1}: `, {
                    text: btn.textContent.trim(),
                    display: getComputedStyle(btn).display,
                    width: getComputedStyle(btn).width,
                    visible: btn.offsetWidth > 0
                });
            });
        } else {
            console.error('未找到编辑密码按钮容器');
        }
    } else {
        console.error('未找到编辑模态框');
    }
    
    // 检查添加模态框中的密码按钮
    const addModal = document.getElementById('addAccountModal');
    if (addModal) {
        console.log('找到添加模态框');
        const addActions = addModal.querySelector('.password-actions');
        if (addActions) {
            console.log('找到添加密码按钮容器');
            const buttons = addActions.querySelectorAll('button');
            console.log(`找到 ${buttons.length} 个按钮`);
            buttons.forEach((btn, index) => {
                console.log(`按钮 ${index+1}: `, {
                    text: btn.textContent.trim(),
                    display: getComputedStyle(btn).display,
                    width: getComputedStyle(btn).width,
                    visible: btn.offsetWidth > 0
                });
            });
        } else {
            console.error('未找到添加密码按钮容器');
        }
    } else {
        console.error('未找到添加模态框');
    }
    
    console.log('====== 密码按钮调试结束 ======');
    alert('密码按钮调试信息已在控制台输出，请按F12查看');
}

// 初始化应用
async function initializeApp() {
    try {
        console.log('开始初始化应用组件...');
        
        // 获取并检查所有筛选器元素
        const selectors = {
            category: document.getElementById('categorySelect'),
            country: document.getElementById('countrySelect'),
            owner: document.getElementById('ownerSelect'),
            search: document.getElementById('searchInput')
        };

        // 检查并设置筛选器
        Object.entries(selectors).forEach(([key, selector]) => {
            if (!selector) {
                console.error(`未找到${key}选择器`);
                return;
            }
            
            if (key === 'search') {
                selector.addEventListener('input', function(e) {
                    currentFilters.search = e.target.value.toLowerCase();
                    renderAccounts();
                });
            } else {
                selector.addEventListener('change', function(e) {
                    currentFilters[key] = e.target.value;
                    renderAccounts();
                });
            }
        });

        // 并行加载数据
        console.log('开始加载数据...');
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
        console.log('开始加载账号数据...');
        
        // 使用正确的API路径
        const response = await fetch('/account/api/accounts');
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success || !Array.isArray(data.accounts)) {
            throw new Error(data.message || '账号数据格式错误');
        }

        // 更新全局账号数据
        accounts = data.accounts;
        console.log(`成功加载 ${accounts.length} 个账号`);

        // 更新筛选器
        await updateFilters(accounts);

        // 渲染账号列表
        renderAccounts();
        
        return accounts;
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
        // 使用正确的API路径
        const response = await fetch('/account/api/categories');
        
        if (!response.ok) {
            throw new Error(`加载类别失败: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success || !Array.isArray(data.categories)) {
            throw new Error('类别数据格式错误');
        }

        const categories = data.categories;
        console.log(`成功加载 ${categories.length} 个类别`);

        // 更新类别选择器
        const categorySelect = document.getElementById('categorySelect');
        const editCategory = document.getElementById('editCategory');
        
        if (categorySelect) {
            categorySelect.innerHTML = '<option value="">全部类别</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
        }
        
        if (editCategory) {
            editCategory.innerHTML = '<option value="">请选择类别</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                editCategory.appendChild(option);
            });
        }

        return categories;
    } catch (error) {
        console.error('加载类别失败:', error);
        showAlert('加载类别失败: ' + error.message, false);
        return [];
    }
}

// 显示错误消息
function showAlert(message, isSuccess = true) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${isSuccess ? 'alert-success' : 'alert-danger'} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

// 渲染账号列表
function renderAccounts() {
    console.log('渲染账号列表...');
    console.log('当前筛选条件:', currentFilters);

    const filteredAccounts = accounts.filter(account => {
        const matchesCategory = !currentFilters.category || account.category === currentFilters.category;
        const matchesCountry = !currentFilters.country || account.country === currentFilters.country;
        const matchesOwner = !currentFilters.owner || account.owner === currentFilters.owner;
        const matchesSearch = !currentFilters.search || 
            (account.platform && account.platform.toLowerCase().includes(currentFilters.search.toLowerCase())) ||
            (account.username && account.username.toLowerCase().includes(currentFilters.search.toLowerCase()));

        return matchesCategory && matchesCountry && matchesOwner && matchesSearch;
    });

    console.log(`筛选后账号数: ${filteredAccounts.length}`);

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

    // 渲染账号列表
    const accountList = document.getElementById('accountList');
    if (!accountList) {
        console.error('未找到账号列表元素');
        return;
    }

    accountList.innerHTML = '';
    if (currentPageAccounts.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `<td colspan="7" class="text-center">没有找到符合条件的账号</td>`;
        accountList.appendChild(emptyRow);
    } else {
        currentPageAccounts.forEach(account => {
            const row = renderAccountRow(account);
            accountList.appendChild(row);
        });
    }

    // 更新分页
    updatePagination(totalPages);
}

// 渲染单个账号行
function renderAccountRow(account) {
    const row = document.createElement('tr');
    
    // 平台/网址
    let platformCell = `
        <td>
            <div class="platform-info">
                <div class="platform-name">${account.platform || ''}</div>
    `;
    
    if (account.website_url) {
        platformCell += `
            <div class="website-url">
                <a href="#" onclick="visitWebsite('${account.website_url}', ${account.id}); return false;" target="_blank">
                    <i class="fas fa-external-link-alt"></i> 访问网站
                </a>
            </div>
        `;
    }
    
    platformCell += `</div></td>`;
    
    // 其他字段
    row.innerHTML = `
        ${platformCell}
        <td>${account.category || ''}</td>
        <td>${account.owner || ''}</td>
        <td>${account.username || ''}</td>
        <td>
            <div class="password-field">
                <input type="password" value="${account.password || ''}" readonly>
                <button class="btn btn-sm" onclick="togglePassword(this, '${account.password || ''}')">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm" onclick="copyPassword('${account.password || ''}')">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </td>
        <td>${account.country ? account.country + (account.region ? '/' + account.region : '') : ''}</td>
        <td>
            <div class="actions">
                <button class="btn btn-outline-primary btn-sm" onclick="editAccount(${account.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteAccount(${account.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </td>
    `;
    
    return row;
}

// 更新分页
function updatePagination(totalPages) {
    const paginationContainer = document.getElementById('pageNumbers');
    if (!paginationContainer) return;
    
    paginationContainer.innerHTML = '';
    
    // 确定要显示的页码范围
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // 添加首页按钮
    if (startPage > 1) {
        const firstPageBtn = document.createElement('button');
        firstPageBtn.className = 'btn-page';
        firstPageBtn.textContent = '1';
        firstPageBtn.onclick = () => changePage(1);
        paginationContainer.appendChild(firstPageBtn);
        
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'page-ellipsis';
            ellipsis.textContent = '...';
            paginationContainer.appendChild(ellipsis);
        }
    }
    
    // 添加页码按钮
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `btn-page ${i === currentPage ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => changePage(i);
        paginationContainer.appendChild(pageBtn);
    }
    
    // 添加末页按钮
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'page-ellipsis';
            ellipsis.textContent = '...';
            paginationContainer.appendChild(ellipsis);
        }
        
        const lastPageBtn = document.createElement('button');
        lastPageBtn.className = 'btn-page';
        lastPageBtn.textContent = totalPages;
        lastPageBtn.onclick = () => changePage(totalPages);
        paginationContainer.appendChild(lastPageBtn);
    }
}

// 切换页码
function changePage(page) {
    if (typeof page === 'string') {
        if (page === 'prev') {
            currentPage = Math.max(1, currentPage - 1);
        } else if (page === 'next') {
            const totalPages = Math.ceil(accounts.length / itemsPerPage);
            currentPage = Math.min(totalPages, currentPage + 1);
        }
    } else {
        currentPage = page;
    }
    
    renderAccounts();
}

// 切换密码显示/隐藏
function togglePassword(button, password) {
    const inputField = button.previousElementSibling;
    if (inputField.type === 'password') {
        inputField.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        inputField.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

// 添加账号的密码显示/隐藏
function toggleAddPassword() {
    const inputField = document.getElementById('password');
    const copyButton = document.querySelector('#addAccountModal .password-actions button:nth-child(2)');
    
    if (inputField.type === 'password') {
        inputField.type = 'text';
        // 显示复制按钮
        if (copyButton) {
            copyButton.style.display = 'flex';
            console.log('显示添加密码的复制按钮');
        }
    } else {
        inputField.type = 'password';
        // 隐藏复制按钮
        if (copyButton) {
            copyButton.style.display = 'none';
            console.log('隐藏添加密码的复制按钮');
        }
    }
}

// 复制添加账号的密码
async function copyAddPassword() {
    const password = document.getElementById('password').value;
    if (!password) {
        showAlert('没有密码可复制', false);
        return;
    }
    
    try {
        await navigator.clipboard.writeText(password);
        showAlert('密码已复制到剪贴板', true);
    } catch (error) {
        console.error('复制密码失败:', error);
        showAlert('复制密码失败', false);
    }
}

// 复制密码
async function copyPassword(password) {
    try {
        await navigator.clipboard.writeText(password);
        showAlert('密码已复制到剪贴板', true);
    } catch (error) {
        console.error('复制密码失败:', error);
        showAlert('复制密码失败', false);
    }
}

// 切换编辑密码显示/隐藏
function toggleEditPassword() {
    const inputField = document.getElementById('editPassword');
    const copyButton = document.querySelector('#editModal .password-actions button:nth-child(2)');
    
    if (inputField.type === 'password') {
        inputField.type = 'text';
        // 显示复制按钮
        if (copyButton) {
            copyButton.style.display = 'flex';
            console.log('显示编辑密码的复制按钮');
        }
    } else {
        inputField.type = 'password';
        // 隐藏复制按钮
        if (copyButton) {
            copyButton.style.display = 'none';
            console.log('隐藏编辑密码的复制按钮');
        }
    }
}

// 复制编辑密码
async function copyEditPassword() {
    const password = document.getElementById('editPassword').value;
    if (!password) {
        showAlert('没有密码可复制', false);
        return;
    }
    
    try {
        await navigator.clipboard.writeText(password);
        showAlert('密码已复制到剪贴板', true);
    } catch (error) {
        console.error('复制密码失败:', error);
        showAlert('复制密码失败', false);
    }
}

// 编辑账号
async function editAccount(id) {
    try {
        console.log('开始编辑账号', id);
        
        // 使用正确的API路径
        const response = await fetch(`/account/api/accounts/${id}`);
        if (!response.ok) {
            throw new Error(`获取账号详情失败: ${response.status}`);
        }
        
        const data = await response.json();
        if (!data.success || !data.account) {
            throw new Error(data.message || '获取账号详情失败');
        }
        
        const account = data.account;
        
        // 填充表单
        document.getElementById('editId').value = account.id;
        document.getElementById('editPlatform').value = account.platform || '';
        document.getElementById('editWebsiteUrl').value = account.website_url || '';
        document.getElementById('editUsername').value = account.username || '';
        document.getElementById('editPassword').value = ''; // 不显示密码，需要用户重新输入
        
        // 尝试选择类别
        const categorySelect = document.getElementById('editCategory');
        if (categorySelect) {
            // 先检查是否已有该选项
            let found = false;
            for (let i = 0; i < categorySelect.options.length; i++) {
                if (categorySelect.options[i].value === account.category) {
                    categorySelect.selectedIndex = i;
                    found = true;
                    break;
                }
            }
            
            // 如果没有该选项但有类别值，添加它
            if (!found && account.category) {
                const option = document.createElement('option');
                option.value = account.category;
                option.textContent = account.category;
                categorySelect.appendChild(option);
                categorySelect.value = account.category;
            }
        }
        
        document.getElementById('editOwner').value = account.owner || '';
        document.getElementById('editCountry').value = account.country || '';
        document.getElementById('editRegion').value = account.region || '';
        document.getElementById('editDescription').value = account.description || '';
        document.getElementById('editNotes').value = account.notes || '';
        
        // 打开模态框
        const editModal = new bootstrap.Modal(document.getElementById('editModal'));
        editModal.show();
    } catch (error) {
        console.error('编辑账号时出错:', error);
        showAlert('编辑账号失败: ' + error.message, false);
    }
}

// 提交编辑表单
async function submitEditForm() {
    try {
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

        // 检查密码字段
        const password = document.getElementById('editPassword').value;
        if (password.trim()) {
            data.password = password;
        }

        // 使用正确的API路径
        const response = await fetch(`/account/api/accounts/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`服务器错误: ${response.status}`);
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || '更新失败');
        }

        showAlert('账号更新成功', true);
        closeEditModal();
        await loadAccounts(); // 重新加载账号列表
        await loadPopularWebsites(); // 更新热门网站列表
    } catch (error) {
        console.error('更新账号失败:', error);
        showAlert('更新账号失败: ' + error.message, false);
    }
}

// 关闭编辑模态框
function closeEditModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
    if (modal) {
        modal.hide();
    }
    
    // 手动移除模态框背景
    setTimeout(() => {
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.classList.remove('show');
            backdrop.classList.remove('fade');
            backdrop.remove();
        });
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }, 300);
}

// 删除账号
async function deleteAccount(id) {
    if (!confirm('确定要删除这个账号吗？此操作不可恢复。')) return;

    try {
        showAlert('正在删除账号...', true);

        // 使用正确的API路径
        const response = await fetch(`/account/api/accounts/${id}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        // 检查响应的Content-Type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (response.ok) {
                showAlert('账号删除成功', true);
                await loadAccounts(); // 重新加载账号列表
                await loadPopularWebsites(); // 更新热门网站列表
            } else {
                throw new Error(data.message || '删除失败');
            }
        } else {
            // 如果响应不是JSON格式
            throw new Error(`删除失败: 服务器返回状态码 ${response.status}`);
        }
    } catch (error) {
        console.error('删除账号时发生错误:', error);
        showAlert('删除账号失败: ' + error.message, false);
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

        // 使用正确的API路径
        const response = await fetch('/account/api/accounts/popular');
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || '获取热门网站失败');
        }

        if (!Array.isArray(data.accounts)) {
            throw new Error('热门网站数据格式错误');
        }

        // 直接使用API返回的数据，不需要再次过滤
        const popularWebsites = data.accounts;
        console.log(`热门网站数量: ${popularWebsites.length}`);

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
            if (website && website.platform) {
                const websiteElement = document.createElement('div');
                websiteElement.className = 'popular-item';
                
                let websiteContent = `
                    <div class="website-rank">${index + 1}</div>
                    <div class="website-info">
                        <div class="website-name">${website.platform}</div>
                `;
                
                // 如果有URL，添加访问链接
                if (website.website_url) {
                    websiteContent += `
                        <a href="#" class="website-link" onclick="visitWebsite('${website.website_url}', ${website.id}); return false;">
                            <i class="fas fa-external-link-alt"></i> 访问
                        </a>
                    `;
                }
                
                websiteContent += `
                    </div>
                    <div class="click-count">${website.click_count || 0} 次</div>
                `;
                
                websiteElement.innerHTML = websiteContent;
                popularWebsitesContainer.appendChild(websiteElement);
            }
        });
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

// 访问网站并增加点击次数
async function visitWebsite(url, accountId) {
    // 先在新标签页中打开网站
    window.open(url, '_blank');
    
    // 然后异步增加点击次数
    try {
        // 使用正确的API路径
        await fetch(`/account/api/accounts/increment_click/${accountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        console.error('记录点击次数失败:', error);
    }
}

// 更新筛选器
async function updateFilters(accounts) {
    try {
        console.log('更新筛选器...');
        
        // 国家筛选器
        const countrySelect = document.getElementById('countrySelect');
        if (countrySelect) {
            const countries = [...new Set(accounts.map(acc => acc.country).filter(Boolean))].sort();
            countrySelect.innerHTML = '<option value="">全部国家</option>';
            countries.forEach(country => {
                const option = document.createElement('option');
                option.value = country;
                option.textContent = country;
                countrySelect.appendChild(option);
            });
        }
        
        // 所有者筛选器
        const ownerSelect = document.getElementById('ownerSelect');
        if (ownerSelect) {
            const owners = [...new Set(accounts.map(acc => acc.owner).filter(Boolean))].sort();
            ownerSelect.innerHTML = '<option value="">全部所有者</option>';
            owners.forEach(owner => {
                const option = document.createElement('option');
                option.value = owner;
                option.textContent = owner;
                ownerSelect.appendChild(option);
            });
        }
        
        console.log('筛选器更新完成');
    } catch (error) {
        console.error('更新筛选器失败:', error);
    }
}

// 下载Excel模板
async function downloadTemplate() {
    try {
        // 使用正确的API路径
        const response = await fetch('/account/api/accounts/download_template');
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
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

// 为下载模板按钮添加事件监听器
document.addEventListener('DOMContentLoaded', function() {
    const downloadTemplateBtn = document.getElementById('downloadTemplate');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', downloadTemplate);
    }
    
    // 为导入按钮添加事件监听器
    const submitImportBtn = document.getElementById('submitImport');
    if (submitImportBtn) {
        submitImportBtn.addEventListener('click', async function() {
            try {
                const form = document.getElementById('importForm');
                if (!form) throw new Error('导入表单不存在');
                
                const fileInput = form.querySelector('input[type="file"]');
                if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                    throw new Error('请选择Excel文件');
                }
                
                const formData = new FormData(form);
                
                // 显示加载状态
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 导入中...';
                
                // 使用正确的API路径
                const response = await fetch('/account/api/accounts/import', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`导入失败: ${response.status}`);
                }
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(`成功导入 ${result.imported_count} 条记录`, true);
                    
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('importModal'));
                    if (modal) modal.hide();
                    
                    // 重新加载账号列表
                    await loadAccounts();
                } else {
                    throw new Error(result.message || '导入失败');
                }
            } catch (error) {
                console.error('导入失败:', error);
                showAlert('导入失败: ' + error.message, false);
            } finally {
                // 恢复按钮状态
                this.disabled = false;
                this.innerHTML = '开始导入';
            }
        });
    }
}); 