// =========================================
// ACCOUNT MANAGEMENT SYSTEM - COMBINED JS
// =========================================

// ------------------- ACCOUNT_FIXED.JS -------------------
// 账号管理系统 API 测试脚本
console.log('测试脚本已加载 - 版本 20250414-1');

// ------------------- MODAL.JS -------------------
// 通用的模态框功能
function initModalFunctionality() {
    // 初始化所有模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        // 创建模态框实例
        const modalInstance = new bootstrap.Modal(modal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });

        // 添加关闭按钮事件
        const closeButtons = modal.querySelectorAll('[data-bs-dismiss="modal"]');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                modalInstance.hide();
            });
        });

        // 添加模态框关闭事件
        modal.addEventListener('hidden.bs.modal', function() {
            // 重置表单
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
            // 移除背景遮罩层
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
        });
    });
}

// 密码显示/隐藏功能
function togglePasswordVisibility(input, button) {
    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '隐藏密码';
    } else {
        input.type = 'password';
        button.textContent = '显示密码';
    }
}

// 复制密码功能
async function copyPassword(password) {
    try {
        const success = await window.copyToClipboard(password);
        if (success) {
            showAlert('密码已复制到剪贴板', true);
        } else {
            showAlert('复制失败', false);
        }
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 显示提示信息
function showAlert(message, isSuccess = true) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${isSuccess ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.maxWidth = '500px';
    alertDiv.style.whiteSpace = 'pre-line'; // 支持换行符
    
    // 如果是错误信息，增加显示时间
    const autoHideTime = isSuccess ? 3000 : 8000;
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 自动消失
    setTimeout(() => {
        alertDiv.remove();
    }, autoHideTime);
}

// ------------------- FILTERS.JS -------------------
// 筛选器初始化和事件处理
function initializeFilters(accounts) {
    if (!Array.isArray(accounts)) return;
    
    // 获取筛选下拉框元素
    const categorySelect = document.getElementById('categorySelect');
    const countrySelect = document.getElementById('countrySelect');
    const ownerSelect = document.getElementById('ownerSelect');
    
    if (!categorySelect || !countrySelect || !ownerSelect) return;
    
    // 清空现有选项，只保留"全部"选项
    categorySelect.innerHTML = '<option value="">全部</option>';
    countrySelect.innerHTML = '<option value="">全部</option>';
    ownerSelect.innerHTML = '<option value="">全部</option>';
    
    // 获取唯一的类别、国家和所有者
    const categories = [...new Set(accounts.map(acc => acc.category).filter(Boolean))];
    const countries = [...new Set(accounts.map(acc => acc.country).filter(Boolean))];
    const owners = [...new Set(accounts.map(acc => acc.owner).filter(Boolean))];

    // 更新类别选项
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categorySelect.appendChild(option);
    });

    // 更新国家选项
    countries.forEach(country => {
        const option = document.createElement('option');
        option.value = country;
        option.textContent = country;
        countrySelect.appendChild(option);
    });

    // 更新所有者选项
    owners.forEach(owner => {
        const option = document.createElement('option');
        option.value = owner;
        option.textContent = owner;
        ownerSelect.appendChild(option);
    });
    
    // 为筛选器添加事件监听
    categorySelect.addEventListener('change', applyFilters);
    countrySelect.addEventListener('change', applyFilters);
    ownerSelect.addEventListener('change', applyFilters);
    
    // 为搜索输入框添加事件监听
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
}

// 应用筛选
function applyFilters() {
    const selectedCategory = document.getElementById('categorySelect')?.value || '';
    const selectedCountry = document.getElementById('countrySelect')?.value || '';
    const selectedOwner = document.getElementById('ownerSelect')?.value || '';
    const searchText = document.getElementById('searchInput')?.value.toLowerCase() || '';

    const accountRows = document.querySelectorAll('#accountList tr');
    
    accountRows.forEach(row => {
        const category = row.querySelector('td:nth-child(2)')?.textContent || '';
        const country = row.querySelector('td:nth-child(6)')?.textContent || '';
        const owner = row.querySelector('td:nth-child(3)')?.textContent || '';
        const platform = row.querySelector('td:nth-child(1)')?.textContent.toLowerCase() || '';
        const username = row.querySelector('td:nth-child(4)')?.textContent.toLowerCase() || '';

        const matchesCategory = !selectedCategory || category === selectedCategory;
        const matchesCountry = !selectedCountry || country === selectedCountry;
        const matchesOwner = !selectedOwner || owner === selectedOwner;
        const matchesSearch = !searchText || 
                            platform.includes(searchText) || 
                            username.includes(searchText);

        row.style.display = (matchesCategory && matchesCountry && matchesOwner && matchesSearch) 
                          ? '' 
                          : 'none';
    });
}

// ------------------- ACCOUNT_MANAGER.JS -------------------
// 全局变量存储账号数据和筛选条件
let accounts = [];
let currentFilters = {
    category: '',
    country: '',
    owner: '',
    search: ''
};
let currentPage = 1;
const itemsPerPage = 20;

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
        
        // 初始化模态框功能
        initModalFunctionality();
        
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

// 更新筛选器
async function updateFilters(accounts) {
    initializeFilters(accounts);
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
                
                // 添加点击事件 - 点击热门网站时筛选右侧账号列表
                websiteElement.addEventListener('click', function() {
                    filterByPlatform(website.platform);
                });
                
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

// 根据平台名称筛选账号
function filterByPlatform(platformName) {
    console.log(`开始筛选平台: ${platformName}`);
    
    // 清空其他筛选条件
    document.getElementById('categorySelect').value = '';
    document.getElementById('countrySelect').value = '';
    document.getElementById('ownerSelect').value = '';
    
    // 设置搜索框的值为平台名称
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = platformName;
        
        // 更新全局筛选条件
        currentFilters.search = platformName.toLowerCase();
        currentFilters.category = '';
        currentFilters.country = '';
        currentFilters.owner = '';
        
        // 高亮显示被点击的热门网站
        const popularItems = document.querySelectorAll('.popular-item');
        popularItems.forEach(item => {
            const websiteName = item.querySelector('.website-name')?.textContent;
            if (websiteName === platformName) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        
        // 添加清除筛选按钮，如果不存在
        if (!document.getElementById('clearFilter')) {
            const searchBox = document.querySelector('.search-box');
            if (searchBox) {
                const clearBtn = document.createElement('button');
                clearBtn.id = 'clearFilter';
                clearBtn.className = 'btn btn-sm btn-outline-secondary clear-filter';
                clearBtn.innerHTML = '<i class="fas fa-times"></i> 清除筛选';
                clearBtn.addEventListener('click', clearFilters);
                searchBox.appendChild(clearBtn);
            }
        }
        
        // 重新渲染账号列表
        renderAccounts();
        
        // 滚动到账号列表
        const accountTable = document.querySelector('.account-table-wrapper');
        if (accountTable) {
            if (window.innerWidth < 768) { // 移动设备上
                accountTable.scrollIntoView({ behavior: 'smooth' });
            }
        }
        
        // 显示筛选提示
        showAlert(`已筛选平台：${platformName}`, true);
    }
}

// 清除所有筛选条件
function clearFilters() {
    // 清空筛选条件
    document.getElementById('categorySelect').value = '';
    document.getElementById('countrySelect').value = '';
    document.getElementById('ownerSelect').value = '';
    document.getElementById('searchInput').value = '';
    
    // 更新全局筛选条件
    currentFilters.search = '';
    currentFilters.category = '';
    currentFilters.country = '';
    currentFilters.owner = '';
    
    // 移除热门网站高亮
    const popularItems = document.querySelectorAll('.popular-item');
    popularItems.forEach(item => {
        item.classList.remove('active');
    });
    
    // 移除清除筛选按钮
    const clearBtn = document.getElementById('clearFilter');
    if (clearBtn) {
        clearBtn.remove();
    }
    
    // 重新渲染账号列表
    renderAccounts();
    
    // 显示提示
    showAlert('已清除所有筛选条件', true);
}

// 访问网站并增加点击次数
async function visitWebsite(url, accountId) {
    // 先在新标签页中打开网站
    window.open(url, '_blank');
    
    // 然后异步增加点击次数
    try {
        // 获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // 使用正确的API路径
        const response = await fetch(`/account/api/accounts/increment_click/${accountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            console.log('点击次数更新成功');
        } else {
            console.error('点击次数更新失败:', data.message);
        }
    } catch (error) {
        console.error('记录点击次数失败:', error);
    }
}

// 渲染账号列表
function renderAccounts() {
    const accountListElement = document.getElementById('accountList');
    if (!accountListElement) {
        console.error('账号列表元素不存在');
        return;
    }

    // 筛选账号
    const filteredAccounts = accounts.filter(account => {
        const matchesCategory = !currentFilters.category || account.category === currentFilters.category;
        const matchesCountry = !currentFilters.country || account.country === currentFilters.country;
        const matchesOwner = !currentFilters.owner || account.owner === currentFilters.owner;
        
        const searchLower = currentFilters.search.toLowerCase();
        const matchesSearch = !searchLower || 
                              (account.platform && account.platform.toLowerCase().includes(searchLower)) ||
                              (account.username && account.username.toLowerCase().includes(searchLower));
        
        return matchesCategory && matchesCountry && matchesOwner && matchesSearch;
    });

    // 计算分页
    const totalPages = Math.ceil(filteredAccounts.length / itemsPerPage);
    if (currentPage > totalPages && totalPages > 0) {
        currentPage = totalPages;
    }
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedAccounts = filteredAccounts.slice(startIndex, startIndex + itemsPerPage);

    // 渲染账号列表
    accountListElement.innerHTML = '';
    
    if (paginatedAccounts.length === 0) {
        accountListElement.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">没有找到匹配的账号</td>
            </tr>
        `;
    } else {
        paginatedAccounts.forEach(account => {
            accountListElement.appendChild(renderAccountRow(account));
        });
    }

    // 更新分页控件
    updatePagination(totalPages);
    
    // 更新总记录数
    const totalItemsElement = document.getElementById('totalItems');
    if (totalItemsElement) {
        totalItemsElement.textContent = filteredAccounts.length;
    }
}

// 渲染账号行
function renderAccountRow(account) {
    const row = document.createElement('tr');
    
    // 平台/网址
    const platformCell = document.createElement('td');
    platformCell.className = 'platform-cell';
    if (account.website_url) {
        platformCell.innerHTML = `
            <a href="#" onclick="visitWebsite('${account.website_url}', ${account.id}); return false;" class="website-link" title="点击访问网站">
                ${account.platform}
                <i class="fas fa-external-link-alt"></i>
            </a>
        `;
    } else {
        platformCell.textContent = account.platform;
    }
    row.appendChild(platformCell);
    
    // 类别
    const categoryCell = document.createElement('td');
    categoryCell.textContent = account.category || '';
    row.appendChild(categoryCell);
    
    // 账户归属
    const ownerCell = document.createElement('td');
    ownerCell.textContent = account.owner || '';
    row.appendChild(ownerCell);
    
    // 用户名
    const usernameCell = document.createElement('td');
    usernameCell.className = 'username-cell';
    usernameCell.textContent = account.username || '';
    row.appendChild(usernameCell);
    
    // 调试账号数据
    console.log('账号数据:', {
        id: account.id,
        platform: account.platform,
        username: account.username,
        password_field: account.encrypted_password,
        has_password: !!account.encrypted_password
    });
    
    // 密码
    const passwordCell = document.createElement('td');
    passwordCell.className = 'password-cell';
    
    // 检查密码字段
    let passwordValue = account.encrypted_password || account.password || '';
    if (!passwordValue) {
        console.warn(`账号 ${account.id} (${account.platform}) 没有密码数据`);
    }
    
    passwordCell.innerHTML = `
        <div class="password-field">
            <div class="password-text-container">
                <span class="password-text">••••••••</span>
                <button class="btn btn-sm btn-toggle" onclick="togglePassword(this, '${passwordValue}')" title="显示密码">
                    <i class="fas fa-eye-slash"></i>
                </button>
            </div>
            <button class="btn btn-sm btn-copy" onclick="copyListPassword('${passwordValue}')" title="复制密码">
                <i class="fas fa-copy"></i>
            </button>
        </div>
    `;
    row.appendChild(passwordCell);
    
    // 国家/地区
    const locationCell = document.createElement('td');
    let locationText = '';
    if (account.country && account.region) {
        locationText = `${account.country} - ${account.region}`;
    } else if (account.country) {
        locationText = account.country;
    } else if (account.region) {
        locationText = account.region;
    }
    locationCell.textContent = locationText;
    row.appendChild(locationCell);
    
    // 更新日期
    const updatedAtCell = document.createElement('td');
    updatedAtCell.className = 'updated-at-cell';
    if (account.updated_at) {
        const updatedDate = new Date(account.updated_at);
        updatedAtCell.textContent = updatedDate.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } else {
        updatedAtCell.textContent = '-';
    }
    row.appendChild(updatedAtCell);
    
    // 操作
    const actionsCell = document.createElement('td');
    actionsCell.className = 'actions-cell';
    actionsCell.innerHTML = `
        <div class="btn-group">
            <button class="btn btn-sm btn-info" onclick="viewAccountDetail(${account.id})" title="查看详情">
                <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-sm btn-primary" onclick="editAccount(${account.id})" title="编辑">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="deleteAccount(${account.id})" title="删除">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    row.appendChild(actionsCell);
    
    return row;
}

// 更新分页控件
function updatePagination(totalPages) {
    const paginationElement = document.getElementById('pageNumbers');
    if (!paginationElement) return;
    
    paginationElement.innerHTML = '';
    
    if (totalPages <= 1) {
        document.getElementById('pagination').style.display = 'none';
        return;
    }
    
    document.getElementById('pagination').style.display = 'flex';
    
    // 显示最多5个页码按钮
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageButton = document.createElement('button');
        pageButton.className = `btn-page ${i === currentPage ? 'active' : ''}`;
        pageButton.textContent = i;
        pageButton.onclick = () => changePage(i);
        paginationElement.appendChild(pageButton);
    }
}

// 切换页面
function changePage(page) {
    if (page === 'prev') {
        if (currentPage > 1) {
            currentPage--;
            renderAccounts();
        }
    } else if (page === 'next') {
        const totalPages = Math.ceil(accounts.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderAccounts();
        }
    } else {
        currentPage = page;
        renderAccounts();
    }
}

// 切换密码显示
function togglePassword(button, password) {
    const passwordField = button.closest('.password-field');
    const passwordText = passwordField.querySelector('.password-text');
    
    console.log('切换密码显示/隐藏', {
        currentContent: passwordText.textContent,
        passwordParam: password,
        hasPassword: !!password,
        passwordLength: password ? password.length : 0
    });
    
    if (passwordText.textContent === '••••••••') {
        // 显示密码
        if (!password) {
            passwordText.textContent = '[无密码数据]';
            showAlert('无法显示密码：数据不可用', false);
        } else {
            passwordText.textContent = password;
        }
        passwordText.classList.add('visible-password');
        button.innerHTML = '<i class="fas fa-eye"></i>';
        button.title = '隐藏密码';
    } else {
        // 隐藏密码
        passwordText.textContent = '••••••••';
        passwordText.classList.remove('visible-password');
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
        button.title = '显示密码';
    }
}

// 修改列表中的复制密码功能
async function copyListPassword(password) {
    try {
        const success = await window.copyToClipboard(password);
        if (success) {
            showAlert('密码已复制到剪贴板', true);
        } else {
            showAlert('复制失败', false);
        }
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 编辑模态框中密码显示/隐藏功能
function toggleEditPassword() {
    const passwordInput = document.getElementById('editPassword');
    const toggleButton = document.querySelector('#editModal .password-actions button:nth-child(1)');
    const copyButton = document.querySelector('#editModal .password-actions button:nth-child(2)');
    
    console.log('切换密码显示状态', {
        passwordInput,
        toggleButton,
        copyButton,
        currentType: passwordInput ? passwordInput.type : 'unknown'
    });
    
    if (passwordInput && toggleButton && copyButton) {
        if (passwordInput.type === 'password') {
            // 显示密码
            passwordInput.type = 'text';
            toggleButton.innerHTML = '<i class="fas fa-eye"></i> 隐藏密码';
            
            // 直接修改DOM属性，完全移除内联display样式
            copyButton.classList.add('show-copy-btn');
            copyButton.removeAttribute('style');
            // 强制设置样式
            copyButton.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important;';
            
            console.log('密码已显示，复制按钮应该可见');
        } else {
            // 隐藏密码
            passwordInput.type = 'password';
            toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i> 显示密码';
            
            // 隐藏复制按钮
            copyButton.classList.remove('show-copy-btn');
            copyButton.style.cssText = 'display: none !important;';
            
            console.log('密码已隐藏，复制按钮已隐藏');
        }
    } else {
        console.error('无法找到密码输入框或按钮元素');
    }
    
    // 检查DOM状态
    setTimeout(() => {
        if (copyButton) {
            console.log('复制按钮当前样式:', {
                display: getComputedStyle(copyButton).display,
                visibility: getComputedStyle(copyButton).visibility,
                opacity: getComputedStyle(copyButton).opacity,
                width: copyButton.offsetWidth,
                height: copyButton.offsetHeight,
                isVisible: copyButton.offsetWidth > 0 && copyButton.offsetHeight > 0
            });
        }
    }, 100);
}

// 修改编辑模态框中的复制密码功能
async function copyEditPassword() {
    const passwordInput = document.getElementById('editPassword');
    if (!passwordInput) {
        console.error('未找到编辑密码输入框');
        return;
    }

    const password = passwordInput.value;
    if (!password) {
        showAlert('没有可复制的密码', false);
        return;
    }

    try {
        const success = await window.copyToClipboard(password);
        if (success) {
            showAlert('密码已复制到剪贴板', true);
        } else {
            showAlert('复制失败', false);
        }
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 添加模态框中密码显示/隐藏功能
function toggleAddPassword() {
    const passwordInput = document.getElementById('password');
    const toggleButton = document.querySelector('#addAccountModal .password-actions button:nth-child(1)');
    const copyButton = document.querySelector('#addAccountModal .password-actions button:nth-child(2)');
    
    console.log('切换添加密码显示状态', {
        passwordInput,
        toggleButton,
        copyButton,
        currentType: passwordInput ? passwordInput.type : 'unknown'
    });
    
    if (passwordInput && toggleButton && copyButton) {
        if (passwordInput.type === 'password') {
            // 显示密码
            passwordInput.type = 'text';
            toggleButton.innerHTML = '<i class="fas fa-eye"></i> 隐藏密码';
            
            // 直接修改DOM属性，完全移除内联display样式
            copyButton.classList.add('show-copy-btn');
            copyButton.removeAttribute('style');
            // 强制设置样式
            copyButton.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important;';
            
            console.log('添加密码已显示，复制按钮应该可见');
        } else {
            // 隐藏密码
            passwordInput.type = 'password';
            toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i> 显示密码';
            
            // 隐藏复制按钮
            copyButton.classList.remove('show-copy-btn');
            copyButton.style.cssText = 'display: none !important;';
            
            console.log('添加密码已隐藏，复制按钮已隐藏');
        }
    } else {
        console.error('无法找到添加密码输入框或按钮元素');
    }
}

// 修改添加模态框中的复制密码功能
async function copyAddPassword() {
    const passwordInput = document.getElementById('password');
    if (!passwordInput) {
        console.error('未找到添加密码输入框');
        return;
    }

    const password = passwordInput.value;
    if (!password) {
        showAlert('没有可复制的密码', false);
        return;
    }

    try {
        const success = await window.copyToClipboard(password);
        if (success) {
            showAlert('密码已复制到剪贴板', true);
        } else {
            showAlert('复制失败', false);
        }
    } catch (err) {
        console.error('复制失败:', err);
        showAlert('复制失败', false);
    }
}

// 编辑账号
async function editAccount(id) {
    try {
        console.log(`开始编辑账号 ID: ${id}`);
        
        // 查找账号数据
        const account = accounts.find(acc => acc.id === id);
        if (!account) {
            throw new Error(`未找到ID为 ${id} 的账号`);
        }
        
        console.log('找到账号数据:', account);
        
        // 填充编辑表单
        document.getElementById('editId').value = account.id;
        document.getElementById('editPlatform').value = account.platform || '';
        document.getElementById('editWebsiteUrl').value = account.website_url || '';
        document.getElementById('editUsername').value = account.username || '';
        const passwordValue = account.encrypted_password || account.password || '';
        document.getElementById('editPassword').value = passwordValue; // 自动填充密码
        document.getElementById('editCountry').value = account.country || '';
        document.getElementById('editRegion').value = account.region || '';
        document.getElementById('editDescription').value = account.description || '';
        document.getElementById('editNotes').value = account.notes || '';
        document.getElementById('editOwner').value = account.owner || '';
        
        // 设置类别选择器
        const editCategory = document.getElementById('editCategory');
        if (editCategory) {
            // 尝试找到匹配的选项
            const options = Array.from(editCategory.options);
            const matchingOption = options.find(option => option.value === account.category);
            
            if (matchingOption) {
                matchingOption.selected = true;
            } else if (account.category) {
                // 如果没有匹配的选项但账号有类别，添加一个新选项
                const newOption = document.createElement('option');
                newOption.value = account.category;
                newOption.textContent = account.category;
                newOption.selected = true;
                editCategory.appendChild(newOption);
            }
        }
        
        // 显示编辑模态框
        const editModal = new bootstrap.Modal(document.getElementById('editModal'));
        editModal.show();
        
        // 如果有密码，显示复制按钮
        if (passwordValue) {
            setTimeout(() => {
                const copyButton = document.querySelector('#editModal .password-actions button:nth-child(2)');
                if (copyButton) {
                    copyButton.classList.add('show-copy-btn');
                    copyButton.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important;';
                }
            }, 300);
        }
        
    } catch (error) {
        console.error('编辑账号失败:', error);
        showAlert('编辑账号失败: ' + error.message, false);
    }
}

// 提交编辑表单
async function submitEditForm() {
    try {
        console.log('提交编辑表单...');
        
        // 获取表单数据
        const id = document.getElementById('editId').value;
        const formData = {
            platform: document.getElementById('editPlatform').value,
            website_url: document.getElementById('editWebsiteUrl').value,
            category: document.getElementById('editCategory').value,
            username: document.getElementById('editUsername').value,
            country: document.getElementById('editCountry').value,
            region: document.getElementById('editRegion').value,
            description: document.getElementById('editDescription').value,
            notes: document.getElementById('editNotes').value,
            owner: document.getElementById('editOwner').value
        };
        
        // 如果有输入密码，也包含密码字段
        const password = document.getElementById('editPassword').value;
        if (password) {
            formData.password = password;
        }
        
        // 检查必填字段
        if (!formData.platform || !formData.username) {
            throw new Error('平台/网址和用户名为必填项');
        }
        
        console.log('编辑账号数据:', formData);
        
        // 获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        // 发送API请求
        const response = await fetch(`/account/api/accounts/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || '更新账号失败');
        }
        
        // 关闭模态框
        const editModal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
        if (editModal) {
            editModal.hide();
        }
        
        // 显示成功消息
        showAlert('账号更新成功', true);
        
        // 重新加载账号列表
        await loadAccounts();
        
    } catch (error) {
        console.error('更新账号失败:', error);
        showAlert('更新账号失败: ' + error.message, false);
    }
}

// 删除账号
async function deleteAccount(id) {
    try {
        // 确认删除
        if (!confirm(`确定要删除这个账号吗？此操作不可恢复。`)) {
            console.log('用户取消删除操作');
            return;
        }
        
        console.log(`开始删除账号 ID: ${id}`);
        
        // 获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        // 发送API请求
        const response = await fetch(`/account/api/accounts/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || '删除账号失败');
        }
        
        // 显示成功消息
        showAlert('账号删除成功', true);
        
        // 重新加载账号列表
        await loadAccounts();
        
    } catch (error) {
        console.error('删除账号失败:', error);
        showAlert('删除账号失败: ' + error.message, false);
    }
}

// 下载Excel模板
async function downloadTemplate() {
    try {
        console.log('开始下载Excel模板...');
        
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

// 提交批量导入
async function submitImport() {
    try {
        console.log('开始提交批量导入...');
        
        // 获取文件
        const fileInput = document.getElementById('excelFile');
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            throw new Error('请选择Excel文件');
        }
        
        const file = fileInput.files[0];
        if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
            throw new Error('请选择Excel文件（.xlsx或.xls格式）');
        }
        
        // 显示加载状态
        const submitButton = document.getElementById('submitImport');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 导入中...';
        }
        
        // 创建FormData对象
        const formData = new FormData();
        formData.append('file', file);
        
        // 获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        // 发送API请求
        const response = await fetch('/account/api/accounts/import', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            if (response.status === 400 && errorData.validation_errors) {
                // 显示验证错误详情
                let errorMessage = errorData.message + '\n\n';
                errorData.validation_errors.forEach(error => {
                    errorMessage += '• ' + error + '\n';
                });
                throw new Error(errorMessage);
            } else {
                throw new Error(`HTTP错误: ${response.status}`);
            }
        }
        
        const result = await response.json();
        
        // 恢复按钮状态
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '开始导入';
        }
        
        if (!result.success) {
            throw new Error(result.message || '导入失败');
        }
        
        // 关闭模态框
        const importModal = bootstrap.Modal.getInstance(document.getElementById('importModal'));
        if (importModal) {
            importModal.hide();
        }
        
        // 显示成功消息
        showAlert(`导入成功: 已导入 ${result.imported_count || 0} 条记录`, true);
        
        // 重新加载账号列表
        await loadAccounts();
        
    } catch (error) {
        console.error('导入失败:', error);
        showAlert('导入失败: ' + error.message, false);
        
        // 恢复按钮状态
        const submitButton = document.getElementById('submitImport');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '开始导入';
        }
    }
}

// 页面加载后执行初始化
document.addEventListener('DOMContentLoaded', async function() {
    console.log('账号管理系统 - 初始化中...');
    
    // 初始化密码按钮状态
    initPasswordButtons();
    
    // 初始化应用
    await initializeApp();
    
    // 绑定下载模板按钮事件
    const downloadTemplateBtn = document.getElementById('downloadTemplate');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', downloadTemplate);
        console.log('下载模板按钮事件已绑定');
    } else {
        console.error('未找到下载模板按钮');
    }
    
    // 绑定导入按钮事件
    const submitImportBtn = document.getElementById('submitImport');
    if (submitImportBtn) {
        submitImportBtn.addEventListener('click', submitImport);
        console.log('导入按钮事件已绑定');
    }
}); 

// 查看账号详情
function viewAccountDetail(accountId) {
    window.location.href = `/account/accounts/${accountId}`;
}