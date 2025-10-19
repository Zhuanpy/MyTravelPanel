// =========================================
// 账号-供应商关联扩展功能
// =========================================

// 全局供应商数据
let suppliers = [];

// 加载供应商列表
async function loadSuppliers() {
    try {
        console.log('开始加载供应商数据...');
        
        const response = await fetch('/account/api/suppliers');
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('供应商API响应:', data);
        
        if (!data.success) {
            throw new Error(data.message || '获取供应商列表失败');
        }
        
        if (!Array.isArray(data.suppliers)) {
            console.warn('供应商数据不是数组:', data.suppliers);
            suppliers = [];
        } else {
            suppliers = data.suppliers;
        }
        
        console.log(`✅ 成功加载 ${suppliers.length} 个供应商`);
        console.log('供应商列表:', suppliers);

        // 更新各个下拉框
        updateSupplierSelects();
        
        return suppliers;
    } catch (error) {
        console.error('❌ 加载供应商数据失败:', error);
        suppliers = [];
        // 不抛出错误，允许页面继续工作
        return [];
    }
}

// 更新所有供应商下拉框
function updateSupplierSelects() {
    // 更新编辑模态框中的供应商选择器
    const editSupplierSelect = document.getElementById('editSupplier');
    if (editSupplierSelect) {
        updateSupplierOptions(editSupplierSelect);
    }
    
    // 更新添加模态框中的供应商选择器
    const addSupplierSelect = document.getElementById('supplier');
    if (addSupplierSelect) {
        updateSupplierOptions(addSupplierSelect);
    }
    
    // 更新筛选器中的供应商选择器
    const filterSupplierSelect = document.getElementById('supplierSelect');
    if (filterSupplierSelect) {
        updateSupplierFilterOptions(filterSupplierSelect);
    }
}

// 更新供应商选项（用于表单）
function updateSupplierOptions(selectElement) {
    // 清空现有选项（保留第一个"无关联"选项）
    while (selectElement.options.length > 1) {
        selectElement.remove(1);
    }
    
    // 如果没有供应商，添加提示选项
    if (suppliers.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '暂无供应商，请先添加供应商';
        option.disabled = true;
        selectElement.appendChild(option);
        
        // 高亮显示添加供应商的提示
        const parentDiv = selectElement.closest('.col-lg-3, .col-md-4, .col-sm-6');
        if (parentDiv) {
            const helpText = parentDiv.querySelector('.text-muted');
            if (helpText) {
                helpText.style.color = '#dc3545';
                helpText.style.fontWeight = 'bold';
            }
        }
    } else {
        // 添加供应商选项
        suppliers.forEach(supplier => {
            const option = document.createElement('option');
            option.value = supplier.supplier_id;
            option.textContent = `${supplier.name} (${supplier.supplier_type_display})`;
            selectElement.appendChild(option);
        });
    }
}

// 更新供应商筛选器选项
function updateSupplierFilterOptions(selectElement) {
    // 清空现有选项（保留前两个选项："全部"和"无关联"）
    while (selectElement.options.length > 2) {
        selectElement.remove(2);
    }
    
    // 如果没有供应商，添加提示
    if (suppliers.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '暂无供应商';
        option.disabled = true;
        selectElement.appendChild(option);
    } else {
        // 添加供应商选项
        suppliers.forEach(supplier => {
            const option = document.createElement('option');
            option.value = supplier.supplier_id;
            option.textContent = `${supplier.name} (${supplier.supplier_type_display})`;
            selectElement.appendChild(option);
        });
    }
}

// 页面加载时立即执行
document.addEventListener('DOMContentLoaded', async function() {
    console.log('供应商扩展脚本开始初始化...');
    
    // 立即加载供应商数据
    await loadSuppliers();
    
    // 添加供应商筛选器事件监听
    const supplierSelect = document.getElementById('supplierSelect');
    if (supplierSelect) {
        supplierSelect.addEventListener('change', function(e) {
            if (typeof currentFilters !== 'undefined') {
                currentFilters.supplier = e.target.value;
                if (typeof renderAccounts === 'function') {
                    renderAccounts();
                }
            }
        });
    }
    
    console.log('供应商扩展初始化完成，已加载供应商数据');
});

// 不再需要扩展筛选器逻辑，已在 account_combined.js 中实现

// 获取供应商名称
function getSupplierName(supplierId) {
    if (!supplierId) return '无关联';
    
    // 如果供应商列表还没加载完成
    if (!suppliers || suppliers.length === 0) {
        console.warn('供应商列表未加载，返回加载中...');
        return '加载中...';
    }
    
    const supplier = suppliers.find(s => s.supplier_id == supplierId);
    if (!supplier) {
        console.warn(`找不到供应商ID: ${supplierId}`);
        return `ID:${supplierId}`;
    }
    return supplier.name;
}

// 导出函数供全局使用
window.loadSuppliers = loadSuppliers;
window.getSupplierName = getSupplierName;
window.updateSupplierSelects = updateSupplierSelects;

console.log('账号-供应商关联扩展已加载');

