// 筛选器初始化和事件处理
document.addEventListener('DOMContentLoaded', function() {
    // 获取筛选下拉框元素
    const categorySelect = document.getElementById('categorySelect');
    const countrySelect = document.getElementById('countrySelect');
    const ownerSelect = document.getElementById('ownerSelect');

    // 为筛选器添加事件监听
    categorySelect.addEventListener('change', applyFilters);
    countrySelect.addEventListener('change', applyFilters);
    ownerSelect.addEventListener('change', applyFilters);

    // 初始化筛选器选项
    function initializeFilters(accounts) {
        if (!Array.isArray(accounts)) return;
        
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
    }

    // 应用筛选
    function applyFilters() {
        const selectedCategory = categorySelect.value;
        const selectedCountry = countrySelect.value;
        const selectedOwner = ownerSelect.value;
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

    // 在加载账号数据后初始化筛选器
    window.addEventListener('accountsLoaded', function(event) {
        const accounts = event.detail;
        initializeFilters(accounts);
    });

    // 为搜索输入框添加事件监听
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
}); 